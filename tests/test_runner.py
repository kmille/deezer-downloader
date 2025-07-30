import sys
import pytest
from deezer_downloader.cli import runner
import types

# No additional imports needed.
def test_version_flag(monkeypatch, capsys):
    """
    Test that the '-v' flag prints the version string (via a patched importlib.metadata.version)
    and exits with a zero status code.
    """
    # Patch the version function to always return "1.2.3"
    def fake_version(pkg):
        if pkg == "deezer_downloader":
            return "1.2.3"
        raise Exception("Unexpected package")
    monkeypatch.setattr("importlib.metadata.version", fake_version)
    
    # Set sys.argv to simulate calling the command with the -v flag.
    test_argv = ["runner.py", "-v"]
    monkeypatch.setattr(sys, "argv", test_argv)
    
    # Running main() should print the version and exit with status code 0.
    with pytest.raises(SystemExit) as exit_info:
        runner.main()
    
    # Ensure that the exit code is 0 (indicating success).
    assert exit_info.value.code == 0
    
    # Capture and assert that the version string appears in the output.
    captured = capsys.readouterr().out
    assert "1.2.3" in captured
def test_no_args_prints_help_and_exits(monkeypatch, capsys):
    """
    Test that running the CLI without any arguments prints the help message and exits with status code 1.
    """
    # Set sys.argv to simulate running the command without any arguments.
    monkeypatch.setattr(sys, "argv", ["runner.py"])
    
    with pytest.raises(SystemExit) as exit_info:
        runner.main()
    
    # Assert that the exit code is 1 when no arguments are provided.
    assert exit_info.value.code == 1
    
    # Check that the output contains the help message (look for the usage line).
    output = capsys.readouterr().out
    assert "usage:" in output.lower()
def test_show_config_template_flag(monkeypatch, capsys):
    """
    Test that using the '-t' flag prints the config template content and exits with status code 0.
    This is done by patching the Path.read_text method so that it returns a fake template content.
    """
    # Save the original read_text method.
    original_read_text = runner.Path.read_text
    # Define a fake read_text that returns fake content when the file name matches the template.
    def fake_read_text(self, encoding=None):
        if self.name == "deezer-downloader.ini.template":
            return "fake config template content"
        return original_read_text(self, encoding)
    
    # Monkeypatch the read_text method for Path so that any instance representing the config template file returns our fake content.
    monkeypatch.setattr(runner.Path, "read_text", fake_read_text)
    
    # Set sys.argv to simulate calling the command with the '-t' flag.
    monkeypatch.setattr(sys, "argv", ["runner.py", "-t"])
    
    # Running main() should detect the -t flag, print the template content, and exit with code 0.
    with pytest.raises(SystemExit) as exit_info:
        runner.main()
    
    # Capture the output and ensure that the exit status is 0.
    captured = capsys.readouterr().out
    assert exit_info.value.code == 0
    assert "fake config template content" in captured
def test_config_flag_calls_load_config_and_run_backend(monkeypatch):
    """
    Test that passing the '-c' flag with a value calls the load_config function with the provided argument
    and then calls run_backend.
    """
    # Create a fake configuration module with a fake load_config function.
    fake_conf_module = types.ModuleType("deezer_downloader.configuration")
    config_called = {}
    def fake_load_config(config_path):
        config_called['config'] = config_path
    fake_conf_module.load_config = fake_load_config
    # Inject the fake module into sys.modules so it is imported in runner.main().
    monkeypatch.setitem(sys.modules, "deezer_downloader.configuration", fake_conf_module)
    # Simulate passing the '-c' flag with a dummy configuration file.
    test_argv = ["runner.py", "-c", "dummy_config.ini"]
    monkeypatch.setattr(sys, "argv", test_argv)
    # Override run_backend in runner to simply record that it was called.
    run_backend_called = [False]
    def fake_run_backend():
        run_backend_called[0] = True
    monkeypatch.setattr(runner, 'run_backend', fake_run_backend)
    # Call main() and verify that it processes the -c flag correctly.
    # Note: main() does not exit when a -c flag is provided, it calls run_backend.
    runner.main()
    # Check that load_config was called with the provided config filename.
    assert config_called.get('config') == "dummy_config.ini"
    # Check that run_backend was called.
    assert run_backend_called[0] is Trueimport sys
import types


def test_run_backend_waitress_called(monkeypatch):
    """
    Test that run_backend calls waitress.serve with the fake app and correct listen string
    when __name__ is not '__main__'.
    """
    # Create a fake configuration with a fake http object.
    class FakeHTTP:
        host = "127.0.0.1"
        def getint(self, key):
            return 8080

    fake_config = types.SimpleNamespace(http=FakeHTTP())

    # Create a fake configuration module.
    fake_conf_module = types.ModuleType("deezer_downloader.configuration")
    fake_conf_module.config = fake_config
    # Provide a dummy load_config to bypass configuration loading.
    fake_conf_module.load_config = lambda config_path=None: None
    monkeypatch.setitem(sys.modules, "deezer_downloader.configuration", fake_conf_module)

    # Create a fake web.app module with a dummy WSGI app.
    fake_app = lambda environ, start_response: None  # a dummy WSGI application
    fake_web_app_module = types.ModuleType("deezer_downloader.web.app")
    fake_web_app_module.app = fake_app
    monkeypatch.setitem(sys.modules, "deezer_downloader.web.app", fake_web_app_module)

    # Create a flag dictionary to record the call to waitress.serve.
    called = {"called": False, "app": None, "listen": None}
    def fake_waitress_serve(app_arg, listen):
        called["called"] = True
        called["app"] = app_arg
        called["listen"] = listen

    # Patch waitress.serve in the runner module.
    monkeypatch.setattr(runner.waitress, "serve", fake_waitress_serve)

    # Call run_backend. Since __name__ in runner is not '__main__', it should call waitress.serve.
    runner.run_backend()

    # Verify that waitress.serve was called with the fake app and correct listen string.
    assert called["called"] is True
    assert called["app"] == fake_app
    assert called["listen"] == "127.0.0.1:8080"
import sys
import types


from deezer_downloader.cli import runner

def test_run_backend_waitress_called(monkeypatch):
    """
    Test that run_backend calls waitress.serve with the fake app and correct listen string
    when __name__ is not '__main__'. The fake configuration uses a dictionary with an 'http'
    key mapping to a FakeHTTP instance that mimics subscript access and a getint method.
    """
    # Create a fake configuration with a fake http object.
    class FakeHTTP:
        def __init__(self):
            self.host = "127.0.0.1"
        def getint(self, key):
            return 8080
        def __getitem__(self, key):
            if key == "host":
                return self.host
            raise KeyError(key)

    fake_config = {'http': FakeHTTP()}

    # Create a fake configuration module.
    fake_conf_module = types.ModuleType("deezer_downloader.configuration")
    fake_conf_module.config = fake_config
    # Provide a dummy load_config to bypass configuration loading.
    fake_conf_module.load_config = lambda config_path=None: None
    monkeypatch.setitem(sys.modules, "deezer_downloader.configuration", fake_conf_module)

    # Create a fake web.app module with a dummy WSGI app.
    fake_app = lambda environ, start_response: None  # a dummy WSGI application
    fake_web_app_module = types.ModuleType("deezer_downloader.web.app")
    fake_web_app_module.app = fake_app
    monkeypatch.setitem(sys.modules, "deezer_downloader.web.app", fake_web_app_module)

    # Create a flag dictionary to record the call to waitress.serve.
    called = {"called": False, "app": None, "listen": None}
    def fake_waitress_serve(app_arg, listen):
        called["called"] = True
        called["app"] = app_arg
        called["listen"] = listen

    # Patch waitress.serve in the runner module.
    monkeypatch.setattr(runner.waitress, "serve", fake_waitress_serve)

    # Call run_backend. Since __name__ in runner is not '__main__', it should call waitress.serve.
    runner.run_backend()

    # Verify that waitress.serve was called with the fake app and correct listen string.
    assert called["called"] is True
    assert called["app"] == fake_app
    assert called["listen"] == "127.0.0.1:8080"
import sys
import types
from deezer_downloader.cli import runner


def test_run_backend_waitress_called(monkeypatch):
    """
    Test that run_backend calls waitress.serve with the fake app and correct listen string
    when __name__ is not '__main__'. The fake configuration uses a FakeHTTP instance that mimics
    the http configuration. This test ensures that waitress.serve is correctly called when the
    runner is imported as a module (and not run as a script).
    """
    # Create a fake configuration with a fake http object.
    class FakeHTTP:
        def __init__(self):
            self.host = "127.0.0.1"
        def getint(self, key):
            return 8080
        def __getitem__(self, key):
            if key == "host":
                return self.host
            raise KeyError(key)

    fake_config = {'http': FakeHTTP()}

    # Create a fake configuration module.
    fake_conf_module = types.ModuleType("deezer_downloader.configuration")
    fake_conf_module.config = fake_config
    # Provide a dummy load_config to bypass configuration loading.
    fake_conf_module.load_config = lambda config_path=None: None
    monkeypatch.setitem(sys.modules, "deezer_downloader.configuration", fake_conf_module)

    # Create a fake web.app module with a dummy WSGI app.
    fake_app = lambda environ, start_response: None  # a dummy WSGI application
    fake_web_app_module = types.ModuleType("deezer_downloader.web.app")
    fake_web_app_module.app = fake_app
    monkeypatch.setitem(sys.modules, "deezer_downloader.web.app", fake_web_app_module)

    # Create a flag dictionary to record the call to waitress.serve.
    called = {"called": False, "app": None, "listen": None}
    def fake_waitress_serve(app_arg, listen):
        called["called"] = True
        called["app"] = app_arg
        called["listen"] = listen

    # Patch waitress.serve in the runner module.
    monkeypatch.setattr(runner.waitress, "serve", fake_waitress_serve)

    # Call run_backend. Since __name__ in runner is not '__main__', it should call waitress.serve.
    runner.run_backend()

    # Verify that waitress.serve was called with the fake app and correct listen string.
    assert called["called"] is True
    assert called["app"] == fake_app
    assert called["listen"] == "127.0.0.1:8080"
