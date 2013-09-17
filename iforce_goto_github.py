import sublime, sublime_plugin
import webbrowser

class IforceGotoGithubCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        webbrowser.open_new_tab("https://github.com/palaniraja/iForce")

