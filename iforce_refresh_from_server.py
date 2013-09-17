import os, platform
import sublime, sublime_plugin


class IforceRefreshFromServerCommand(sublime_plugin.WindowCommand):
    currentProjectFolder = None
    antBin = None

    def run(self, *args, **kwargs):
        if platform.system() == 'Windows':
            self.antBin = 'ant.bat'
        else:
            self.antBin = 'ant'
        
        self.currentProjectFolder = self.window.folders()[0]
        print ('iForce: Prj Path: ' + self.currentProjectFolder)
        # os.chdir(folder)
        self.window.run_command('exec', {'cmd': [self.antBin, "-file", "iForce_build.xml", "-propertyfile", "iForce_build.properties", "getLatest"], 'working_dir':self.currentProjectFolder})
