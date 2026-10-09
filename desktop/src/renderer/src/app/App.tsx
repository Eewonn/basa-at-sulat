import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router'
import { ToastProvider } from '@/components/ui'
import { AppShell } from './AppShell'
import { ClassScreen } from '@/screens/ClassScreen'
import { CheckScreen } from '@/screens/CheckScreen'
import { ReviewScreen } from '@/screens/ReviewScreen'
import { LearnerScreen } from '@/screens/LearnerScreen'
import { PracticeScreen } from '@/screens/PracticeScreen'
import { BooksScreen, CheckIndexScreen, SettingsScreen } from '@/screens/OtherScreens'
import { LangContext, type Lang } from '@/strings'

const queryClient = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false } } })

function savedLang(): Lang {
  try {
    return localStorage.getItem('lang') === 'en' ? 'en' : 'fil'
  } catch {
    return 'fil'
  }
}

export function App() {
  const [lang, setLangState] = useState<Lang>(savedLang)
  const setLang = (l: Lang) => {
    setLangState(l)
    try {
      localStorage.setItem('lang', l)
    } catch {
      // Language just won't persist; nothing else depends on it.
    }
  }

  return (
    <LangContext.Provider value={{ lang, setLang }}>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <MemoryRouter>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<ClassScreen />} />
                <Route path="learner/:learnerId" element={<LearnerScreen />} />
                <Route path="check" element={<CheckIndexScreen />} />
                <Route path="check/:learnerId" element={<CheckScreen />} />
                <Route path="review/:assessmentId" element={<ReviewScreen />} />
                <Route path="books" element={<BooksScreen />} />
                <Route path="settings" element={<SettingsScreen />} />
              </Route>
              {/* Kid mode: full screen, no sidebar. */}
              <Route path="practice/:learnerId" element={<PracticeScreen />} />
            </Routes>
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    </LangContext.Provider>
  )
}
