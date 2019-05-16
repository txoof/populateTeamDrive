#!/usr/bin/env ipython
#!/usr/bin/env python
# coding: utf-8


# In[2]:


#get_ipython().magic(u'load_ext autoreload')
#get_ipython().magic(u'autoreload 2')

#get_ipython().magic(u'alias nbconvert nbconvert portfolioCreator.ipynb')




# In[3]:


#get_ipython().magic(u'nbconvert')




# In[4]:


import logging
import logging.config
import os
import json
import datetime
# import ConfigParser
import sys
import signal
import re
from glob import glob
import csv
import textwrap
import configuration
from gdrive.auth import getCredentials
from gdrive.gdrive import googledrive, GDriveError
from humanfriendly import prompts
from progressbar import ProgressBar, Bar, Counter, ETA,     AdaptiveETA, Percentage




# In[5]:


def resource_path(relative_path):
    """ Get absolute path to resource, works for ide and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)




# In[6]:


def setup_logging(
    default_config=None,
    default_level=logging.INFO,
    output_path='~/', 
    env_key='LOG_CFG'):
    """Setup logging configuration
    borrowed from: https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/

    """
    path = default_config
    value = os.getenv(env_key, None)
    config = None
    if value:
        path = value
    if os.path.exists(path):
        try:
            with open(path, 'rt') as f:
                config = json.load(f)
        except Exception as e:
            print('failed to read logging configuration')
            return(None)

        # set the specific path to store log files
        if config:
            if output_path:
                for handler in config['handlers']:
                    if 'filename' in config['handlers'][handler]:
                        logFile = os.path.basename(config['handlers'][handler]['filename'])
                        logPath = os.path.expanduser(output_path+'/')

                        if not os.path.isdir(logPath):
                            try:
                                os.makedirs(logPath)
                            except OSError as e:
                                logging.error('failed to make log file directory: {}'.format(e))
                                logging.error('using {} instead'.format(config['handlers'][handler]['filename']))
                                break

                        config['handlers'][handler]['filename'] = logPath+logFile


            logging.config.dictConfig(config)
            logging.getLogger().setLevel(default_level)
            return(config)
        else:
            return(None)

    else:
        logging.basicConfig(level=default_level)
        return(None)




# In[7]:


def fileSearch(path = None, search = None):
        '''search for a file name string in a given path'''
        if not search:
            search = ''
        logger = logging.getLogger(__name__)
        logger.debug('searching path: {0} for \"{1}\"'.format(path, search))
        try:
            searchPath = os.path.expanduser(path)
        except AttributeError as e:
            logger.error('Error: no path specified')
            searchPath = ''
        try:
            allFiles = os.listdir(searchPath)
        except OSError as e:
            logger.error(e)
            return(None)
        
        # list comprehension search with regex
        #http://www.cademuir.eu/blog/2011/10/20/python-searching-for-a-string-within-a-list-list-comprehension/
        regex = re.compile('.*('+search+').*')
        
        return([m.group(0) for l in allFiles for m in [regex.search(l)] if m])




# In[8]:


def getConfiguration(cfgfile):
    # required configuraiton options
    # Section: {'option': 'default value'}
    logger = logging.getLogger(__name__)
    logger.debug('getting configuration')
    cfgpath = os.path.dirname(cfgfile)
    config_required = {
        'Main': {'credentials': os.path.join(cfgpath, 'credentials/'), 
                 'teamdriveID': '',
                 'teamdrivename': '',
                 'folderID': '',
                 'foldername': '',
                 },
        }

    config = configuration.get_config(cfgfile)

    update_config = False

    for section, values in list(config_required.items()):
        if not config.has_section(section):
            logger.warning('section: {} not found in {}'.format(section, cfgfile))
            logger.debug('adding section {}'.format(section))
            config.add_section(section)
            update_config = True
        for option, value in list(values.items()):
            if not config.has_option(section, option):
                logger.warning('option: {} not found in {}'.format(option, cfgfile))
                logger.debug('adding option {}: {}'.format(option, value))

                config.set(section, option, value)
                update_config = True


    # for section, options in config_required.items():

    if update_config:
        try:
            logger.debug('updating configuration file at: {}'.format(cfgfile))
            configuration.create_config(cfgfile, config)
        except Exception as e:
            logger.error(e)
            
    return(config)




# In[9]:


def getTeamDrive(myDrive):
    '''
    menu driven interaction for choosing a writeable team drive
    '''
    #available and writeable team drives
    logger = logging.getLogger(__name__)
    try:
        teamdrives_all = myDrive.listTeamDrives()
    except Exception as e:
        logger.error(e)
    
    if len(teamdrives_all) < 1:
        logger.warning('no writeable team drives found for this user')
        return(None)
    
    teamdrives_writeable = {}
    for drive in teamdrives_all:
        if drive['capabilities']['canAddChildren']:
            teamdrives_writeable[drive['name']] = drive
    
    teamdrive = None
    
    print('Please seledct a Team Drive for storing Portfolio folders from the list below:')
    try:
        teamdrive_name = prompts.prompt_for_choice(choices=sorted(teamdrives_writeable.keys()), default=None)
        teamdrive=teamdrives_writeable[teamdrive_name]
    except prompts.TooManyInvalidReplies as e:
        logger.warning('user failed to make a choice')
    
    return(teamdrive)




# In[32]:


def getPortfolioFolder(myDrive, teamdriveID):
    '''
    menu driven interaction to locate and choose portfolio folder on team drive
    
    returns:
        folder (dictionary) - google drive object properties dictionary
    '''
    logger = logging.getLogger(__name__)
    logger.info('starting search for portfolio folder in teamdrive: {}'.format(teamdriveID))
    
    foldersearch = ''
    attempt = 5
    while (len(foldersearch) <= 0) and (attempt > 0):
        attempt -= 1
        foldersearch = prompts.prompt_for_input(question='Please enter a portion of the portfolio folder name (case insensitive): ',
                                                default=None, strip=True)
        if len(foldersearch) <= 0:
            print(('Nothing entered. {} attempts remain.'.format(attempt)))
            
        searchresult = myDrive.search(name=foldersearch, fuzzy=True, teamdrive = teamdriveID, mimeType='folder')
        if len(searchresult['files']) <= 0:
            print(('No folders contained "{}"'.format(foldersearch)))
            print('Please try entering only part of the folder name')
            foldersearch = ''
            
    
    
    if len(foldersearch) <= 0:
        logger.warning('user entered 0 length string for folder search')
        return(None)
    
    
    foldernames = []
    for each in searchresult['files']:
        foldernames.append(each['name'])
    
    print('Please select the folder that contains the Portfolio Folders')
    try:
        foldername = prompts.prompt_for_choice(choices=foldernames)
    except prompts.TooManyInvalidReplies as e:
        logger.warning('user failed to make a choice')
        return(None)
    
    return(searchresult['files'][foldernames.index(foldername)])




# In[11]:


def getPathfromList(list_path=['~/'], message='Choose from the paths below', default=None):
    '''
    menu driven interaction to select path 
    accepts:
        list_path (list) - list of paths to display
        messager (string) - message to display
        default (string) - default choice (must be one of the items in the list otherwise defaults to None)
    
    returns:
        searchPath (string) - valid and existing path
    '''
    logger = logging.getLogger(__name__)
    logger.debug('path list: {}'.format(list_path))
    searchPath = None
    list_path = sorted(list_path)
    list_path.append('OTHER')
    
    if default not in list_path:
        logging.warning('default ({}) not in list; setting default = None'.format(default))
        default = None
    
    if message:
        print(message)
    searchPath = prompts.prompt_for_choice(choices=list_path, default=default)
    logger.debug('searchPath = {}'.format(searchPath))
    
    if not searchPath is 'OTHER':
        searchPath = os.path.expanduser(searchPath)
    else:
        attempt = 5
        searchPath = None
        while not searchPath and attempt > 0:
            logger.debug('attempts remaining: {}'.format(attempt))
            attempt -= 1
            searchPath = prompts.prompt_for_input('Please type the complete path to use: ')
            logger.debug('searchPath = {}'.format(searchPath))         
    
    if len(searchPath) < 1:
        searchPath = None
    return (searchPath)




# In[12]:


def getFiles(path='~/', pattern='.*', ignorecase=True):
    '''
    search path for files matching pattern (regular expression)
    accepts:
        path (string) - path to search
        pattern (string) - regular expression to search for in file names
        ignorecase (bool) - defaults to True, ignore file name case
    returns:
        list of files matching pattern
        '''

    logger = logging.getLogger(__name__)
    
    path = os.path.expanduser(path+'/*')
    logger.debug('Path: {}, glob pattern: {}, ignorecase: {}'.format(path, pattern, ignorecase))
    
    flags = re.IGNORECASE
    files = []
        
    if ignorecase:
        for eachfile in [f for f in sorted(glob(path), key=os.path.getmtime) if re.match(pattern, f, flags=flags)]:
            files.append(eachfile)
    
    if not ignorecase:
        for eachfile in [f for f in sorted(glob(path), key=os.path.getmtime) if re.match(pattern, f)]:
            files.append(eachfile)        
    
    return(files)




# In[13]:


def chooseFile(path='~/', pattern='.*', ignorecase=True, 
               message='Please choose a file from the list\n**Files are sorted newest at bottom**'):
    '''
    menu interaction for choose a file in the specified path from the file glob created using a regex pattern
    accepts:
        path (string) - path to search
        pattern (string) - regular expression to search for in file names
        ignorecase (bool) - defaults to True, ignore file name case
        message(string) - message to show
    returns:
        selection (string) - selected file'''
    
    logger = logging.getLogger(__name__)
    filelist = getFiles(path=path, pattern=pattern, ignorecase=ignorecase)
    if len(filelist) >= 1:
        logger.debug('filelist: {}'.format(filelist))
        print(message)
        selection = prompts.prompt_for_choice(choices=filelist)
        return(selection)
    else:
        logger.warning('no files matching pattern ({}) at location: {}'.format(pattern, path))
        return(None)




# In[14]:


def fileToList(inputfile, stripWhitespace=True):
    '''
    Creates a list from a text file and optionally strips out whitespace
    '''
    logger = logging.getLogger(__name__)
    logger.debug('inputfile = {}'.format(inputfile))
#     super elegant solution as seen below 
#     https://stackoverflow.com/questions/4842057/easiest-way-to-ignore-blank-lines-when-reading-a-file-in-python
    try:
        with open(inputfile, 'r') as fhandle:
            if stripWhitespace:
                lines = [_f for _f in (line.strip() for line in fhandle) if _f]
            else:
                lines = [line.strip() for line in fhandle]
    except IOError as e:
        logger.debug(e)
    return(lines)




# In[15]:


def checkFolder(folderID, myDrive):
    '''
    Checks properties of a folder id

    returns:
        tuple(isFolder (bool), writeable(bool), properties(dict)) - false if no match
    
    '''
    logger = logging.getLogger(__name__)
    logger.debug('checking folder id: {}'.format(folderID))
    props = None
    isFolder = False
    writeable = False
    try:
        logger.debug('checking properties for ID: {}'.format(folderID))
        props = myDrive.getprops(folderID, 'capabilities, mimeType, name')
    except GDriveError as e:
        logger.error('failed to get properties for {}; {}'.format(folderID, e))
        logger.error('please try again. if this error persists, please try reconfiguring the folder')
        logger.error('cannot continue; exiting')
    
    try:
        if props['mimeType'] == myDrive.mimeTypes['folder']:
            isFolder = True
            logger.debug('this ID is a folder')
        if props['capabilities']['canAddChildren']:
            writeable = True
            logger.debug('this ID is a writable folder')
        else:
            logger.debug('this ID is not a writable folder')
    except (KeyError, TypeError) as e:
        pass
    
    if not props:
        logger.warning('this ID is not a folder')
                
    return(isFolder, writeable, props)




# In[16]:


def mapHeaders(file_csv, expected_headers=[]):
    '''map an expected list of header values to their position in a csv
    accepts:
        file_csv (csv.reader object) 
        expected_headers (list) - list of headers to search for, ignoring all others
    '''
    logger = logging.getLogger(__name__)
    logger.debug('mapping headers')
    
    missing_headers = []
    headerMap = {} 
    
    try:
        csvHeader = file_csv[0]
    except IndexError as e:
        logger.warning('csv empty: {}'.format(e))
        csvHeader = {}
    
    logger.debug('checking for missing headers')
    for each in expected_headers:
        if each not in csvHeader:
            logger.debug('missing: {}'.format(each))
            missing_headers.append(each)
    
    headerMap['missingheaders'] = missing_headers
    
    headerMap['headers'] = {}

    if len(missing_headers) > 0:
        logging.warning('missing headers: {}'.format(missing_headers))
    for index, value in enumerate(csvHeader):
        if value in expected_headers:
            headerMap['headers'][value] = index
    logger.debug('completed mapping headers')
    logger.debug('return: {}'.format(headerMap))
    return(headerMap)




# In[17]:


# mylogger = logging.getLogger(__name__)
# mylogger.setLevel(logging.DEBUG)
# mapHeaders('/Users/aciuffo/Downloads/bad.student.export.text', ['classOf', 'FirstLast', 'Student_Number'])




# In[18]:


def doExit(exit_level=0, testing=False):
    logger = logging.getLogger(__name__)
    logger.info('exiting before completion with exit code {}'.format(exit_level))
    if not testing:
        sys.exit(0)




# In[19]:


def createFolders(myDrive, teamdrive, parentFolder, folderList, progressbar=True):
    '''
    create folders folders in a valid parent folder from a list
    '''
    createdFolders = {}
    logger = logging.getLogger(__name__)
    logger.debug('creating folders')
    logger.debug('checking parent folder: {}'.format(parentFolder))
    
    # Define progress bar widgets for consistent look and feel
    widgets = ['Checking: ', Percentage(), ' ',
               Bar(marker='=',left='[',right=']'), 
               ' Processed ', Counter(),
               ' ', AdaptiveETA()]
    
    folder_check = None
    try:
        folder_check = checkFolder(parentFolder, myDrive)
    except GDriveError as e:
        logger.error('error checking parent folder: {}'.format(e))
    except Exception as e:
        logger.error('critical error: {}'.format(e))
    if not all(folder_check):
        try:
            mimeType = folder_check[2]['mimeType']
        except (TypeError, KeyError) as e:
            mimeType = 'Unknown'
            return(None)
        logger.warning('parent folder cannot be used\n is folder: {}\n is writeable: {}\n mimeType: {}'.format(folder_check[0], folder_check[1], mimeType))
        return(None)

    # init the ProgressBar
    if progressbar:
        pbar = ProgressBar(widgets=widgets, maxval=len(folderList))
        pbar.start()
        pbar_index = 0
        print(('Processing {} folders'.format(len(folderList))))

    for folder in folderList:
        # update the progress bar
        if progressbar:
            pbar.update(pbar_index)
            pbar_index += 1
        
        # expect folder should be created
        createFolder = True
        
        # check if folder already exists
        logger.debug('searching for exisitng folder with name: {}'.format(folder))
        
        try:
            result = myDrive.search(parents=parentFolder, name=folder, trashed=False, mimeType='folder', 
                                    orderBy='createdTime', teamdrive=teamdrive)
        except GDriveError as e:
            logger.error('error searching for folder: {}'.format(e))
            createdFolders[folder] = None
        except Exception as e:
            logger.error('critical error: {}'.format(e))
            logger.error('skipping folder: {}'.format(folder))
            continue
        
        if 'files' in result: 
            if len(result['files']) > 0:
                logger.debug('folder already exists, do not create')
                createFolder = False
                createdFolders[folder] = result['files'][0]
            if len(result['files']) > 1:
                logger.warning('{} folders with the same name ({}) found. Consider removing the newest one'.format(len(result['files']), folder))
        else:
            createFolder = True
            
        if createFolder:
            try:
                result = myDrive.add(name=folder, parents=parentFolder, mimeType='folder')
            except GDriveError as e:
                logger.error('error creating folder: {}'.format(e))
                createdFolders[folder] = None
            except Exception as e:
                logger.error('critical error: {}'.format(e))
                logger.error('skipping folder: {}'.format(folder))
                continue
            
            createdFolders[folder] = result
            
    if progressbar:
        pbar.finish()
        print('Completed\n')
    
    return(createdFolders)




# In[19]:


# studentexport = '/Users/aciuffo/Downloads/SHORT student.export (4).text'
# studentexport_csv = []
# with open(studentexport, 'rU') as csvfile:
#     csvreader = csv.reader(csvfile)
#     for row in csvreader:
#         studentexport_csv.append(row)
# studentexport_csv




# In[20]:


# # studentexport_csv
# headers = mapHeaders(studentexport_csv, ['LastFirst', 'Student_Number', 'ClassOf'])
# # somelist[:] = [x for x in somelist if not determine(x)]
# studentexport_csv[:] = [i for i in studentexport_csv if len(i) >= len(headers['headers'])]
# print studentexport_csv




# In[20]:


def createPortfolioFolders(myDrive, parentFolder, teamdriveID, studentexport_csv, gradefolder_list, headerMap):
    '''
    create folders on google drive if they do not exist
    
    accepts:
        myDrive(googleDrive object)
        folderid (string) - folder id string
        folders (list) - list of folder names
        studentexport_csv - list of lists 
        headerMap - map of fields
    
    returns:
        folderinfo (dict) - {folder name: folder url, or None for failures}
    '''
    logger = logging.getLogger(__name__)
    logger.debug('creating folders at gdrive path: {}'.format(parentFolder))
    # progress bar widgets
    widgets = ['Checking: ', Percentage(), ' ',
               Bar(marker='=',left='[',right=']'), 
               ' Processed ', Counter(),
               ' ', AdaptiveETA()]
    

    # init variables
    studentFolders = {}
    classOfFolders = {}
    classOf_string = 'Class Of-'
    
    # check that google drive parent folder exists and is a folder
    try:
        folder_check = checkFolder(parentFolder, myDrive)
    except GDriveError as e:
        logger.error('error checking parent folder: {}'.format(e))
    except Exception as e:
        logger.error('critical error: {}'.format(e))
    if not all(folder_check):
        try:
            mimeType = folder_check[2]['mimeType']
        except (TypeError, KeyError) as e:
            mimeType = 'Unknown'
            return(None)
        logger.warning('parent folder cannot be used\n is folder: {}\n is writeable: {}\n mimeType: {}'.format(folder_check[0], folder_check[1], mimeType))
        return(None)

    
    # gather all unique and classOf rows from csv and build dictionaries
    logger.debug('gathering "Class Of" folders from student export file')

    # clear out empty or malformed lines in student export csv
    # slice containing only records that have the correct number of elements
    studentexport_csv[:] = [i for i in studentexport_csv if len(i) >= len(headerMap['headers'])]

    
    
    # build dictionaries 
    for student in studentexport_csv[1:]:
#         if len(student) < len(headerMap['headers']):
#             logger.debug('skipping record:')
#             logger.debug('>>{}<<'.format(student))
#             continue
        classOf = student[headerMap['headers']['ClassOf']]
        studentNumber = student[headerMap['headers']['Student_Number']]
        lastFirst = student[headerMap['headers']['LastFirst']]
        name = lastFirst + ' - ' + studentNumber
        
        classOfFolders[classOf] = {}
        classOfFolders[classOf]['name'] = classOf_string + classOf
        
        studentFolders[studentNumber] = {}
        studentFolders[studentNumber]['name'] = name
        studentFolders[studentNumber]['classOf'] = classOf
    
    if len(classOfFolders) <1:
#         print 'No valid rows were found in CSV; cannot continue'
        logger.error('no valid rows found in student export file; cannot continue with this file')
        return(None)
    logger.debug('{} "Class Of" folders found in student export file'.format(len(classOfFolders)))
    logger.debug('{} student records found in student export file'.format(len(studentFolders)))
    
    
    # check for existence of Class Of folders and create if they are missing
    logger.debug('checking for existing "Class Of" folders in google drive')
    
    print(('Checking for or creating {} "Class Of-" folders in portfolio folder'.format(len(classOfFolders))))
    classOfFolders = createFolders(myDrive=myDrive, parentFolder=parentFolder, 
                                   teamdrive=teamdriveID,
                                   folderList=[value.get('name') for key, value in list(classOfFolders.items())])
    
        
        
        
    # create student folders within the class of folders
    
    logger.debug('{} students found in student export file'.format(len(studentexport_csv)-1))
    
    # check for existence of Class Of folders and create if they are missing
    logger.debug('checking for existing student folders in google drive')

    print(('Checking for or creating {} student folders in portfolio folder'.format(len(studentexport_csv)-1)))
    

    # init progress bar for student of folders 
    pbar = ProgressBar(widgets=widgets, maxval=len(studentexport_csv)-1)
    pbar.start()
    pbar_index = 0
    
    for student in studentexport_csv[1:]:
        logger.debug('Processing record:')
        logger.debug('>>{}<<'.format(student))
        # update the progress bar
        pbar.update(pbar_index)
        pbar_index += 1
      
        # start off assuming the folder needs to be created
        createFolder = True
        classOf = student[headerMap['headers']['ClassOf']]
        student_number = student[headerMap['headers']['Student_Number']]
        student_LastFirst = student[headerMap['headers']['LastFirst']]
        folder_name =  student_LastFirst + ' - ' + student_number
        studentFolders[student_number] = {}

        # use the classOf folder ID for the parent
        if classOfFolders['Class Of-'+str(classOf)]:
            classOf_id = classOfFolders['Class Of-'+str(classOf)]['id']
        else:
            logger.error('missing data for parent folder: Class Of-{}; skipping student'.format(classOf))
            studentFolders[student_number] = None
            continue
        
        
        # check if folder already exists
        logger.debug('searching for exisitng folder with name: {}'.format(folder_name))
        
        try:
            result = myDrive.search(parents=classOf_id, name=folder_name, trashed=False, mimeType='folder', 
                                    orderBy='createdTime', teamdrive=teamdriveID)
        except GDriveError as e:
            logger.error('error searching for folder: {}'.format(e))
            createdFolders[folder] = None
        except Exception as e:
            logger.error('critical error: {}'.format(e))
            logger.error('skipping folder: {}'.format(folder_name))
            continue
        
        if 'files' in result: 
            if len(result['files']) > 0:
                logger.debug('folder already exists, do not create')
                createFolder = False
                # use the first in the array
                studentFolders[student_number] = result['files'][0]
                                                        
            if len(result['files']) > 1:
                logger.warning('{} folders with the same name ({}) found. Consider removing the newest one'.format(len(result['files']), folder))
                
        if createFolder:
            logger.debug('creating folder: {}'.format(folder_name))
            try:
                result = myDrive.add(name=folder_name, parents=classOf_id, mimeType='folder',
                                    fields='name, webViewLink, id, mimeType')
            except GDriveError as e:
                logger.error('error creating folder {}: {}'.format(folder_name, e))
                logger.error('skipping folder')
                studentFolders[student_number] = None
                continue
            except Exception as e:
                logger.error('critical error: {}'.format(e))
                studentFolders[student_number] = None
                logger.error('skipping folder')
            

            
            # check the result is OK and record it
            if any(result):
                studentFolders[student_number] = result
            else:
                studentFolders[student_number] = None
                continue
            
        # append the LastFirst field and student number to the dictionary if not None and try to create gradelevel folders
        if any(studentFolders[student_number]):
            studentFolders[student_number]['LastFirst'] = student_LastFirst
            studentFolders[student_number]['classOf'] = classOf
            studentFolders[student_number]['student_number'] = student_number
        
            # create the grade-level folders if needed
            logger.debug('create class of folders')
            if studentFolders[student_number]:
                gradeFolder_result = createFolders(myDrive=myDrive, folderList=gradefolder_list,
                                                   teamdrive=teamdriveID, 
                                                   parentFolder=studentFolders[student_number]['id'], 
                                                   progressbar=False)
            # if there was a failure here record None to indicate the need for a redo
            if not any(gradeFolder_result):
                studentFolders[student_number] = None
        

    # finish updating the pbar for Class Of- Folders
    pbar.finish()
    print('Completed\n')
        
    return(studentFolders)




# In[35]:


def writeCSV(studentFolders, csvHeaders=None, output_path='~/Desktop/myCSV.csv'):
    logger = logging.getLogger(__name__)
    logger.debug('writing csv output at path: {}'.format(output_path))
    
    output_path = os.path.expanduser(output_path)
    htmlFormat = '<a href={}>Right click link and *Open Link in New Tab* to view student folder</a>'
    csvOutput_list = []
    if not csvHeaders:
        csvHeaders = ['webViewLink',
                      'LastFirst',
                      'classOf', 
                      'student_number']
    csvOutput_list.append(csvHeaders)
    for student in studentFolders:
        if studentFolders[student]:
            thisStudent = []
            for header in csvHeaders:
                if header in studentFolders[student]:
                    if header == 'webViewLink':
                        thisStudent.append(htmlFormat.format(studentFolders[student][header]))
                    else:
                        thisStudent.append(studentFolders[student][header])                
                        if len(thisStudent) == len(csvHeaders):
                            csvOutput_list.append(thisStudent)
    
    logger.debug('Writing rows:')
    try:
#         with open(output_path, 'wb') as f:
        with open(output_path, 'w') as f:
            writer = csv.writer(f,
                    quoting = csv.QUOTE_NONE,
                    delimiter='\t')
            for each in csvOutput_list:
                logging.debug(each)
                writer.writerow(each)
#             writer.writerows(csvOutput_list)
    except Exception as e:
        logger.error('error writing CSV file: {}; {}'.format(output_path, e))
        return(None)
    return(output_path)




# In[22]:


# import csv
# my_list = [['a', 'dog'], ['b', 'cat']]
# with open('./foo.txt', 'wb') as f:
#     writer = csv.writer(f, quoting = csv.QUOTE_NONE, delimiter='\t')
#     for each in my_list:
#         writer.writerow(each)




# In[36]:


def main():
    version = '00.10 - 2019.04.18'
    appName = 'portfolioCreator'

    cfgfile = appName+'.ini'
    cfgpath = os.path.join('~/.config/', appName)
    cfgfile = os.path.expanduser(os.path.join(cfgpath, cfgfile))

    logger = logging.getLogger(__name__)
    loggingConfig = resource_path('resources/logging.json')
    setup_logging(default_config=loggingConfig,default_level=logging.ERROR, output_path='~/')
    
    # log level names
    levelNames = ['DEBUG', 'INFO', 'WARNING']
    
    # set the color for human friendly 
    os.environ['HUMANFRIENDLY_HIGHLIGHT_COLOR'] = 'green'

    # set the terminal dimensions
    sys.stdout.write("\x1b[8;{rows};{cols}t".format(rows=50, cols=100))

    
    logging.info('===Starting {} Log==='.format(appName))

    # location of student export files downloaded from powerschool
    studentexport_list = ['~/Downloads', '~/Desktop']
    studentexport = None
    studentexport_path = None

    # assume the configuration file does not need to be updated
    updateConfig = False

    # configuration 
    myConfig = getConfiguration(cfgfile)

    # start with this in case it is never properly set
    teamdriveName = '**UNKNOWN**'

    # for use this for doExit to prevent killing the Jupyter kernel when testing
    testing = False

    # get the log file names
    log_files = []
    for handlers in logger.root.handlers:
        if 'FileHandler' in str(handlers.format.__self__.__class__):
            log_files.append(handlers.baseFilename)

    # set the base path for the output file
    studentCSVoutput_path = studentCSVoutput_path = '~/Desktop/Links_for_PowerSchool_{:%Y-%m-%d_%H.%M.%S}.tsv.txt'
    
    # list to record student ids that had issues during the folder creation process
    failures = []
    ####### set all config options from configuration file
    if myConfig.has_option('Main', 'credentials'):
        credential_store = os.path.expanduser(myConfig.get('Main', 'credentials'))
    else:
        credential_store = os.path.expanduser(os.path.join(cfgpath, 'credentials'))
        updateConfig = True

    if myConfig.has_option('Main', 'teamdriveid'):
        teamdriveID = myConfig.get('Main', 'teamdriveid')
    else:
        teamdriveID = None

    if myConfig.has_option('Main', 'teamdrivename'):
        teamdriveName = myConfig.get('Main', 'teamdrivename')
    else:
        teamdriveName = None

    if myConfig.has_option('Main', 'folderid'):
        folderID = myConfig.get('Main', 'folderid')
    else:
        folderID = None

    if myConfig.has_option('Main', 'foldername'):
        folderName = myConfig.get('Main', 'foldername')
    else:
        folderName = None

    if myConfig.has_option('Main', 'gradefolders'):
        gradefolders = myConfig.get('Main', 'gradefolders')
    else:
#         gradefolders = os.path.join('resources', 'gradefolders.txt')
#         gradefolders = 'resources/gradefolders.txt'
        gradefolders = resource_path('resources/gradefolders.txt')

    if myConfig.has_option('Main', 'useremail'):
        useremail = myConfig.get('Main', 'useremail')
    else:
        useremail = None

    
    if myConfig.has_option('Main', 'loglevel'):
        loglevel = myConfig.get('Main', 'loglevel')
#this is a private attribute - should not use it
        if loglevel in levelNames:

            logger.setLevel(loglevel)
    else:
        loglevel = 'ERROR'
        logger.setLevel(loglevel)
        myConfig.set('Main', 'loglevel', loglevel)
        updateConfig = True

    # print the configuration if the logging level is high enough
    if logging.getLogger().getEffectiveLevel() <= 10:
        config_dict = {}
        for section in myConfig.sections():
            config_dict[section] = {}
            for option in myConfig.options(section):
                config_dict[section][option] = myConfig.get(section, option)

        logger.debug('current configuration:')
        logger.debug('\n{}'.format(config_dict))

    about = resource_path('./resources/about.txt')
    about_list = fileToList(about, False)
    wrapper = textwrap.TextWrapper(replace_whitespace=True, drop_whitespace=True, width=65)
    print(('{} - Version: {}'.format(appName, version)))
    for line in about_list:
        print(('\n'.join(wrapper.wrap(text=line))))

    # begin processing?
    if not prompts.prompt_for_confirmation(question='Would you like to proceed?', default=True):
        print('Exiting')
        doExit(testing=testing)


    # assume that the configuration is NOT ok and that user will want to reconfigure
    proceed = False
    # start with configuration settings from config file; if user chooses to reconfigure offer opportunity to change
    reconfigure = False 
    while not proceed:
        
        # set logging level
        if reconfigure:
            print('If you are having trouble with this program, adjust the logging level.')
            print(('Log level is set to only show: {}'.format(loglevel)))
            if prompts.prompt_for_confirmation(question='Change log level?', default=False):
                loglevel_list = []
#                 for k, v in sorted(levelNames):
                for v in sorted(levelNames):
                    if isinstance(v, str):
                        loglevel_list.append(v)
                
                loglevel = prompts.prompt_for_choice(choices=loglevel_list, default='WARNING')
                
                logging.root.setLevel(loglevel)

                for each in logging.root.handlers:
                    each.setLevel(loglevel)
                

        # attempt to authorize using stored credentials or generate new credentials as needed 
        if reconfigure:
            print(('Currently authenticated Google Drive user: {}'.format(useremail)))
            if prompts.prompt_for_confirmation(question='Reconfigure google drive user?', default=False):
                for f in glob(credential_store+'/*.json'):
                    try:
                        os.remove(f)
                    except Exception as e:
                        logger.error(e)
                        logger.error('could not remove credential store at: {}'.format(credential_store))
                        print(('Error removing stored credentials in folder {}'.format(credential_store)))
                        print(('Please try running this program again. If this message reappears check the logs: {}'.format(log_files)))
                        doExit(testing=testing)

        # get or reset credentials
#         clientSecrets = os.path.join('resources', 'client_secrets.json')
#         clientSecrets = 'resources/client_secrets.json'
        clientSecrets = resource_path('resources/client_secrets.json')
        try:
            credentials = getCredentials(storage_path=credential_store, client_secret=clientSecrets)
        except Exception as e:
            logging.critical(e)

        # configure google drive object

        try:
            myDrive = googledrive(credentials)
        except Exception as e:
            logger.error('Could not set up google drive connection: {}'.format(e))
            print('Could not setup google drive connection. Please run this program again.')
            print(('If this error persists, please check the logs: {}'.format(log_files)))
            print('cannot continue')
            doExit(testing=testing)

        if not useremail:
            logger.warning('No useremail set in configuration file')
            try:
                useremail = myDrive.userinfo['emailAddress']
            except Exception as e:
                logging.error('Error retreving useremail address from drive configuration')
                print('Error fetching configuration information.')
                print('Please run the program again')
                print(('If this error persists, please check the logs: {}'.format(log_files)))
                doExit(testing=testing)
            myConfig.set('Main', 'useremail', useremail)
            updateConfig = True

        if reconfigure:
            print(('Currently selected Team Drive: {}'.format(teamdriveName)))
            if prompts.prompt_for_confirmation(question='Reconfigure Team Drive?', default=False):
                teamdriveID = None
                teamdriveName = None
                folderID = None
                folderName = None


        if not teamdriveID:
            logger.warning('Team Drive ID missing in configuration file')
            try:
                teamdrive = getTeamDrive(myDrive)
            except Exception as e:
                logging.error('Error accessing team drives: e')
                doExit(testing=testing)

            if not teamdrive:
                logger.error('no team drives found')
                logger.error('userinfo: {}'.format(useremail))
                print('No Team Drives located; cannot proceed.')
                print(('You are authenticated as: {}'.format(useremail)))
                logger.error('exiting')
                doExit(testing=testing)

            try:
                teamdriveID = teamdrive['id']
                teamdriveName = teamdrive['name']
            except (KeyError, TypeError) as e:
                logger.error('no valid team drive information found: {}'.format(e))
                logger.error('userinfo: {}'.format(useremail))
                print('No Team Drive was found. Do you have write access to a Team Drive with this account?')
                print(('You are authenticated as: {}'.format(useremail)))
                logger.error('exiting')
                doExit(testing=testing)

            print(('Using Team Drive: {}'.format(teamdriveName)))    
            myConfig.set('Main', 'teamdriveid', teamdriveID)
            myConfig.set('Main', 'teamdriveName', teamdriveName)
            updateConfig = True

        if reconfigure:
            print(('Currently selected portfolio folder: {}'.format(folderName)))
            if prompts.prompt_for_confirmation(question='Reconfigure portfolio folder?', default=False):
                folderName = None
                folderID = None

        if not folderID or not folderName:
            logger.warning('Folder ID or name missing')
            try:
                folder = getPortfolioFolder(myDrive, teamdriveID)
            except GDriveError as e:
                logger.error('Could not search for folder: {}'.format(e))
                print ('There was a problem searching Team Drive for a folder')
                print(('You are authenticated as: {}'.format(useremail)))
            try:
                folderID = folder['id']
                folderName = folder['name']
            except (KeyError, TypeError) as e:
                logger.error('no valid folder information found {}'.format(e))
                logger.error('exiting')
                doExit(testing=testing)

            print(('Using Folder: {} on Team Drive: {}'.format(folderName, teamdriveName)))
            myConfig.set('Main', 'foldername', folderName)
            myConfig.set('Main', 'folderid', folderID)
            updateConfig=True
            
        if not os.path.exists(gradefolders):
            logger.error('failed to locate {}'.format(gradefolders))
            logger.error('exiting')
            print('gradefolders.txt file is missing. Please reinstall the application.')
            doExit(testing=testing)

        # get the gradefolder file
        gradefolder_list = fileToList(gradefolders)

        # check validity of gradefolder
        if len(gradefolder_list) < 1:
            print('grade folder file is corrupt. Please reinstall the application')
            doExit(testing=testing)


        if updateConfig:
            configuration.create_config(cfgfile, myConfig)

    
        # allow reconfiguring selected student export file
        if reconfigure and studentexport:
            print(('Currently selected student export file: {}'.format(studentexport)))
            if prompts.prompt_for_confirmation(question='Select new student export file', default=False):
                studentexport = None            
        
        # # get and validate path for student_export folder
        attempt = 5
        while not studentexport and (attempt > 0):
            logger.debug('remaining attempts to locate student export: {}'.format(attempt))
            attempt -= 1
            if not studentexport:
                # invoke menu for prompting user to choose a path to the studentexport file
                studentexport_path = getPathfromList(studentexport_list, 
                                                     message='Please choose which folder contains the Student Export File.',
                                                     default=studentexport_list[0])


            studentexport = chooseFile(path=studentexport_path, pattern='.*student.*export.*')
            # try again if nothing is returned
            if not studentexport:
                print(('No student exports files found in folder: {}'.format(studentexport_path)))
                print('please place a student export file in that folder or try an alternative location')
                continue
            logger.debug('student export file chosen: {}'.format(studentexport))
            if not os.access(studentexport, os.R_OK):
                print(('Could not read file: {}. Please choose another file'.format(studentexport)))
                logger.error('file is unreadable: {}'.format(studentexport))
                studentexport = None
                
        if not studentexport:
            logger.warning('User was not able to specify student export file')
            if prompts.prompt_for_confirmation(question='It looks like you are having trouble locating a student.export.text file.\nWould you like to try again?'):
                continue
            else:
                doExit(testing=testing)
                
        logger.debug('Student export file: {}'.format(studentexport))

        # read the studentexport text file into a csv object
        studentexport_csv = []
        try: 
            with open(studentexport, 'r') as csvfile: # changed from 'rU' to 'r' 
                csvreader = csv.reader(csvfile)
                for row in csvreader:
                    studentexport_csv.append(row)
        except (OSError, IOError) as e:
            logging.warning('error reading file: {}\n{}'.format(studentexport,e))
            print(('Could not read file: {}'.format(studentexport)))
            print('please try a different file or download a new student.export file before trying again')
            # give user a chance to try again
            studentexport = None
            continue
#             doExit(testing=testing)

        # parse and check validity of student export file
        expected_headers = ['ClassOf', 'Student_Number', 'LastFirst']
        headerMap = mapHeaders(file_csv=studentexport_csv, expected_headers=expected_headers)
    
        if not headerMap or (len(headerMap['headers']) != len(expected_headers)):
            logging.warning('cannot continue without valid header map')
            print(('file: {} appears to not contain the expected header row (in any order): {}'.format(studentexport, expected_headers)))
            if headerMap['missingheaders']:
                print(('your file appears to be missing the field(s): {}'.format(headerMap['missingheaders'])))
            print('please try a different file or download a new student.export file before trying again')
#             doExit(testing=testing)
            studentexport = None
            continue

        logger.debug('asking to proceed with current configuration')
        
        # config variables to print to screen for user:
        config_print = ['useremail', 'teamdrivename', 'foldername']
        print('\n*** Curent Configuration to Use: ***')
        for section in myConfig.sections():
            for option in myConfig.options(section):
                if option in config_print:
                    print(('{} = {}'.format(option, myConfig.get(section, option))))
                    
        print(('studentexport = {}'.format(studentexport)))

        print('\nWould you like to proceed with the configuration above?')
        choices = {'Yes - Proceed with creating folders': (True, False), 'No - Reconfigure my settings': (False, True), 'Quit': True} 
        
        myChoice = prompts.prompt_for_choice(sorted(choices.keys()), padding=True)

        if myChoice is 'Quit':
            doExit(testing=testing)
        else:
            # set proceed and reconfigure to the tuples in choices variable 
            logging.debug('myChoice: {} -> {}'.format(myChoice, choices[myChoice]))
            proceed, reconfigure = choices[myChoice]

        if proceed:
        # # start processing the student export file
            studentFolders = createPortfolioFolders(myDrive, parentFolder=folderID, teamdriveID=teamdriveID, 
                                              studentexport_csv=studentexport_csv, headerMap=headerMap,
                                              gradefolder_list=gradefolder_list)

            if not studentFolders:
                logger.debug('no folders created; trying again')
        #         continue


            for eachStudent in studentFolders:
                if not studentFolders[eachStudent]:
                    failures.append(eachStudent)
                    2

            if len(failures) > 0:
                logger.warning('{} students not processed due to previous errors'.format(len(failures)))
                print(('{} students were not processed due to errors. Please run this batch again. Only missing folders will be created.'.format(len(failures))))
                print ('The following students associated with the student numbers below had problems:')
                print(failures)
                print ('Please run this program again with the same student list. Only missing folders will be created.')
                print(('If errors persist, please check the logs: {}'.format(log_files)))

            # add the time and date to the filename
            studentCSVoutput_path = studentCSVoutput_path.format(datetime.datetime.now()) 
            # use a tab delimiter and extension of .txt for powerschool with no quotes. It is dumb.
            if not writeCSV(output_path=studentCSVoutput_path,
                            studentFolders=studentFolders):
                logger.error('failed to write TSV file: {}'.format(studentCSVoutput_path))
                print ('Writing PowerSchool TSV ouptut failed. Please run this program again.')
                print(('If this error persists please check the logs: {}'.format(log_files)))
            else:
                print(('Completed! Please send the TSV output file ({}) to the PowerSchool Administrator'.format(studentCSVoutput_path)))

                # get input from the user to hold the window open when run from Finder
            if prompts.prompt_for_confirmation(question='Process another file?'):
                proceed = False
                studentexport = False
            else:
                print('exiting')
                break




# In[37]:


if __name__=='__main__':
    main()


