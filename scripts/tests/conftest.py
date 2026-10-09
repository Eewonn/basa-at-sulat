import netguard


def pytest_configure(config):
    netguard.install()
