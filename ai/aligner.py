"""Forced alignment with Meta's MMS aligner (torchaudio.pipelines.MMS_FA), CPU only.

torch is imported lazily, so `import ai` stays cheap for code that never aligns. Weights are cached in
models/torch/ (git-ignored) and downloaded on first use.

We know what the reader was supposed to say, so we don't recognise speech: we line the audio up with the
known letters and ask how well each word fits. A word the reader skipped or said differently can't line
up well, and the aligner can't quietly "correct" it the way a speech recogniser would.
"""
import os
import warnings
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("TORCH_HOME", str(ROOT / "models" / "torch"))

SAMPLE_RATE = 16000


@dataclass
class WordAlignment:
    start_frame: int
    end_frame: int
    token_scores: list = field(default_factory=list)  # probability (0-1) of each letter at its aligned frames


@dataclass
class Alignment:
    words: list  # list[WordAlignment], one per input word
    frame_sec: float  # seconds per model frame (about 0.02)
    duration_sec: float


@dataclass
class Fit:
    gap: float  # forced-alignment log-probability minus the best label's at every frame (0 = perfect, < 0 worse)
    speech_frames: int  # frames where the model's best guess is a letter, not the blank (0 = nothing said)


def fit_gap(audio_path: str, words: list):
    """How well the audio fits these words compared with the model's own best guess, frame by frame (a Fit).

    Total log-probability of the forced alignment to `words` minus that of the best label at every frame,
    so 0 is a perfect fit and more negative is worse. No `*` wildcard: silence is left to the blank, where
    both sides agree, so it costs nothing. This is what tells a lone word from something else (Sanay's
    "Say it"): unlike inside a passage, a lone word isn't pinned by neighbours, so its letters can always
    find *some* frames that fit them a little, and only the comparison shows it wasn't said.
    `speech_frames` says whether anything was said at all: silence is all blank. Without it, a very short
    word (si, ng) can't fall far enough behind to be rejected even in silence.
    Returns None when the audio is too short to hold the words.
    """
    import torch
    import torchaudio.functional as F

    bundle, model, tokenizer, _ = _load(False)  # full precision: see QUANTIZE
    with torch.inference_mode():
        emission, _ = model(load_audio(audio_path))
    log_probs = emission[0, :, : bundle.get_dict()["*"]].contiguous()  # drop the wildcard column
    tokens = torch.tensor([sum(tokenizer(words), [])], dtype=torch.int32)
    try:
        _, scores = F.forced_align(log_probs.unsqueeze(0), tokens, blank=0)
    except RuntimeError as err:
        if "too long" in str(err):
            return None
        raise
    best = log_probs.max(dim=-1)
    return Fit(gap=scores[0].sum().item() - best.values.sum().item(),
               speech_frames=int((best.indices != 0).sum().item()))


def weights_cached() -> bool:
    """True if the aligner weights are already on disk (so loading won't trigger a ~1.2 GB download)."""
    checkpoints = Path(os.environ["TORCH_HOME"]) / "hub" / "checkpoints"
    return checkpoints.is_dir() and any(checkpoints.iterdir())


def warm_up() -> None:
    """Load the models now (a few seconds), so the first score() or check_word() call isn't the slow one.

    Call it once at engine startup. Downloads the weights first if they aren't cached, so on an
    offline laptop they must already be in models/torch/.
    """
    _load(QUANTIZE)
    _load(False)


def model_loaded() -> bool:
    """True once the scoring model is in memory (for GET /health: "loaded" / "not_loaded")."""
    return _load.cache_info().currsize > 0


# Speed (P3-AI-1). Nearly all of the time is the network; alignment itself takes hundredths of a second.
# For score() and word_timings(), int8 weights in its Linear layers plus every hardware thread (instead of
# torch's default of one per core) took scoring from about 40 s to 16 s per minute of audio on our CPU
# laptop (Ryzen 5 7520U). On eval/ the confirmation set didn't change and the tuning set gained one
# borderline false alarm. check_word() keeps full precision: with int8 the model "heard" a frame of speech
# in silence, which its nothing-said check relies on, and its clips are short, so speed doesn't matter there.
# Set BASA_FULL_PRECISION=1 to run everything at full precision.
QUANTIZE = os.environ.get("BASA_FULL_PRECISION") != "1"


@lru_cache(maxsize=2)
def _load(quantized: bool):
    """(bundle, model, tokenizer, aligner); `quantized` gives the int8 model. Cached per kind."""
    import torch
    import torchaudio

    torch.set_num_threads(os.cpu_count() or torch.get_num_threads())
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model()
    model.eval()
    if quantized:
        # torch.ao.quantization is deprecated (removed in torch 2.10); requirements.txt pins 2.8, which
        # forced_align needs anyway. If it's ever missing, run at full precision rather than fail.
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                model = torch.ao.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
        except (AttributeError, ImportError, RuntimeError) as err:
            warnings.warn(f"int8 quantization unavailable ({err}); scoring at full precision, about 1.4x slower")
    return bundle, model, bundle.get_tokenizer(), bundle.get_aligner()


def load_audio(path: str):
    """Mono 16 kHz float tensor of shape (1, samples). wav/flac/ogg; convert other formats with ffmpeg first."""
    import soundfile as sf
    import torch
    import torchaudio.functional as F

    data, sr = sf.read(path, dtype="float32", always_2d=True)
    wav = torch.from_numpy(data.mean(axis=1)).unsqueeze(0)
    return F.resample(wav, sr, SAMPLE_RATE) if sr != SAMPLE_RATE else wav


def align(audio_path: str, words: list, star_at_ends: bool = True):
    """Align normalised words (non-empty a-z/apostrophe strings) to the audio.

    Returns an Alignment, or None when the audio is too short to hold the text (CTC needs at least one
    frame per letter, plus one between repeated letters), which is what a skipped-everything recording is.

    star_at_ends adds the aligner's `*` wildcard before and after the text, so chatter before or after the
    reading doesn't get forced onto the first and last words. It must NOT go between words: `*` costs
    nothing at any frame, so it would swallow real speech and shrink every word to a single frame.
    """
    import torch

    bundle, model, tokenizer, aligner = _load(QUANTIZE)
    wav = load_audio(audio_path)
    with torch.inference_mode():
        emission, _ = model(wav)

    targets = tokenizer(words)
    if star_at_ends:
        star = bundle.get_dict()["*"]
        targets = [[star]] + targets + [[star]]
    try:
        spans = aligner(emission[0], targets)
    except RuntimeError as err:  # "targets length is too long for CTC"
        if "too long" in str(err):
            return None
        raise
    if star_at_ends:
        spans = spans[1:-1]

    out = []
    for word_spans in spans:
        out.append(WordAlignment(
            start_frame=word_spans[0].start,
            end_frame=word_spans[-1].end,
            token_scores=[s.score for s in word_spans],
        ))
    return Alignment(words=out, frame_sec=wav.shape[1] / emission.shape[1] / SAMPLE_RATE,
                     duration_sec=wav.shape[1] / SAMPLE_RATE)
