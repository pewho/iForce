import os, platform
import shutil
import sublime, sublime_plugin
import logging

#Constants
TEST_FOLDER_NAME = 'test'

antBin = 'ant.bat' if platform.system() == 'Windows' else 'ant'

class ObjectType:
	folder = None
	packageTag = None
	extension = None
	hasMetadataFile = None
	def __init__(self, folder, packageTag, extension, hasMetadataFile):
		self.folder = folder
		self.packageTag = packageTag
		self.extension = extension
		self.hasMetadataFile = hasMetadataFile

# Identify the type of object being compiled
objectTypes = [
	ObjectType('classes'        , 'ApexClass'     , 'cls'      , True),
	ObjectType('components'     , 'ApexComponent' , 'component', True),
	ObjectType('objects'        , 'CustomObject'  , 'object'   , False),
	ObjectType('pages'          , 'ApexPage'      , 'page'     , True),
	ObjectType('staticresources', 'StaticResource', 'resource' , True),
	ObjectType('triggers'       , 'ApexTrigger'   , 'trigger'  , True)
]

typesByFolder = {}
for ot in objectTypes:
	typesByFolder[ot.folder] = ot;

def create_metadata_file(sourcefile):
	# If metadata file already exists, do nothing
	metaFile = sourcefile + '-meta.xml'
	if os.path.exists(metaFile):
		return

	# Get required info
	folderpath, filename = os.path.split(sourcefile)
	srcpath, folder = os.path.split(folderpath)
	objectType = typesByFolder[folder]
	if objectType.packageTag == 'ApexPage':
		metaFileContent = '<?xml version="1.0" encoding="UTF-8"?>\n<ApexPage xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>25.0</apiVersion><description>'+filename+'</description><label>'+filename+'</label></ApexPage>'
	else:
		metaFileContent = '<?xml version="1.0" encoding="UTF-8"?>\n<'+objectType.packageTag+' xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>25.0</apiVersion><status>Active</status></'+objectType.packageTag+'>'

	# Create the file
	fhandle = open(metaFile,'w')
	fhandle.write(metaFileContent)
	fhandle.close()

def copy_to_test(sourcefile, test_path):
	# Get required information
	path, filename = os.path.split(sourcefile)
	path, foldername = os.path.split(path)
	objectType = typesByFolder.get(foldername)
	if objectType == None:
		raise ValueError('The file does not appear to be a Force.com file: ' + filename)

	#Ignore all file that aren't ApexClassess
	if objectType.packageTag is not 'ApexClass':
		return

	# Copy files
	targetfolder = test_path + os.sep + foldername
	targetfile = targetfolder + os.sep + filename
	if not os.path.exists(targetfolder):
		os.makedirs(targetfolder)
	shutil.copyfile(sourcefile, targetfile)
	if objectType.hasMetadataFile:
		create_metadata_file(sourcefile)
		shutil.copyfile(sourcefile + '-meta.xml', targetfile + '-meta.xml')

def generate_package_xml(test_path):
	package_path = test_path + os.sep + 'package.xml'

	# Remove package file if it exists already
	if os.path.exists(package_path):
		os.remove(package_path)

	# Open the file and add required headers
	fhandle = open(package_path, 'w')
	fhandle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
	fhandle.write('<Package xmlns="http://soap.sforce.com/2006/04/metadata">')

	# For each recognized type of artifact, add them to the package file
	for ot in objectTypes:
		folder = test_path + os.sep + ot.folder
		if (os.path.exists(folder)):
			fhandle.write('<types>')

			# For each file in that folder, add it's entry
			for f in os.listdir(folder):
				fname, fext = os.path.splitext(f)
				if fext == '.' + ot.extension:
					fhandle.write('<members>' + fname + '</members>')

			fhandle.write('<name>' + ot.packageTag + '</name>')
			fhandle.write('</types>');

	# Close the file
	fhandle.write('<version>25.0</version>')
	fhandle.write('</Package>')
	fhandle.close()


def generate_build_xml(test_path):
	build_path = test_path + os.sep + 'test_build.xml'

	#Remove previous build.xml if exists
	if os.path.exists(build_path):
		os.remove(build_path)

	# Open the file and add required headers
	fhandle = open(build_path, 'w')
	fhandle.write('<project default="env" basedir="." xmlns:sf="antlib:com.salesforce">\n')
	fhandle.write('<property environment="env"/>\n\n')

	fhandle.write('<target name="testopen" description="Test open file">\n')
	fhandle.write('<record name="testOpenClasses.debug" action="start" append="false" />\n')
	fhandle.write('<sf:deploy username="${username}" password="${password}" serverurl="${serverurl}" deployRoot="' + TEST_FOLDER_NAME + '" checkOnly="true" logType="${debuglevel}">\n')
	
	#Build the <runTest> command for each open class
	ot = typesByFolder["classes"]
	folder = test_path + os.sep + ot.folder
	if (os.path.exists(folder)):
		for f in os.listdir(folder):
			fname, fext = os.path.splitext(f)
			if fext == '.' + ot.extension:
				fhandle.write('<runTest>' + fname + '</runTest>\n')

	#Close file
	fhandle.write('</sf:deploy>\n')
	fhandle.write('<record name="testAllClasses.debug" action="stop" />\n')
	fhandle.write('</target>\n')
	fhandle.write('</project>')


def test_files(sublime_command, test_path):
	prj_folder = os.path.dirname(test_path)
	sublime_command.window.run_command('exec', {'cmd': [antBin, "-file", test_path + os.sep + "test_build.xml", "-propertyfile", "iForce_build.properties", "testopen"], 'working_dir':prj_folder})

class iforce_quick_testCommand(sublime_plugin.WindowCommand):
	currentFile = None
	prjFolder = None
	testFolder = None

	def run(self, *args, **kwargs):
		objectType = None # Type of object being compiled

		if self.window.active_view().is_dirty():
			self.window.active_view().run_command('save')

		self.prjFolder = self.window.folders()[0]
		print ('iForce: Project folder path' + self.prjFolder)
		self.testFolder = self.prjFolder + os.sep + TEST_FOLDER_NAME
		print ('iForce: Test folder name' + self.testFolder)

		if (os.path.exists(self.testFolder)):
			try:
				shutil.rmtree(self.testFolder)
				print ('iForce: Old test deleted')
			except Exception as e:
				print ('iForce: Couldn\'t delete old test dir:' + str(e))

		# create dir
		print ('iForce: new Test folder Created')
		os.makedirs(self.testFolder)

		# Copy current file to test folder
		print ('iForce: copy classes on Test folder')
		try:
			currentFiles = self.window.views()
			if len(currentFiles) > 0:
				for f in currentFiles:
					self.currentFile = f.file_name()
					copy_to_test(self.currentFile, self.testFolder)
		except ValueError as e:
			logging.exception('iForce: Unable to copy file to test.')
			sublime.error_message('Unable to copy file to test:\n' + str(e))
			return

		# write package file and deploy
		generate_package_xml(self.testFolder)
		generate_build_xml(self.testFolder)
		test_files(self, self.testFolder)

def test_all_files(sublime_command, test_path):
	sublime_command.window.run_command('exec', {'cmd': [antBin, "-file", test_path + os.sep + "iForce_build.xml", "-propertyfile", test_path + os.sep + "iForce_build.properties", "qtest"], 'working_dir':test_path})

class iforce_quick_test_allCommand(sublime_plugin.WindowCommand):
	prjFolder = None

	def run(self, *args, **kwargs):	
		self.prjFolder = self.window.folders()[0]
		print ('iForce: Project folder path' + self.prjFolder)

		test_all_files(self, self.prjFolder)
