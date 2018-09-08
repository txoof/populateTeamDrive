#!/usr/bin/env ipython

# coding: utf-8

# In[ ]:

import logging
import oauth2client
import httplib2
# from gdrive.auth import getCredentials
from apiclient import discovery
from apiclient import errors 


# In[ ]:

class GDriveError(Exception):
    pass


# In[163]:

# google documentation here:
# https://developers.google.com/apis-explorer/#p/
class googledrive():
    '''
    creates a google drive interface object
    
    Accepts:
    google drive v3 service object: (discover.build('drive', 'v3', credentials = credentials_object)
    
    '''
    def __init__(self, object):
        logger = logging.getLogger(__name__)
        if  not isinstance(object, oauth2client.client.OAuth2Credentials):
            logging.critical('invalid credential object: oauth2client.client.OAtuth2Credentials expected; {} received'.format(type(object)))
#             print ('Error: googleapicleint.discovery.Resource object expected')
#             print ('{:>5}create a resource object:'.format(''))
#             print ('{:>10}credentials = getCredentials(credJSON = "cleint_secret.json")'.format(''))
#             print ('{:>10}service = discovery.build("drive", "v3", credentials=credentials)'.format(''))
#             print ('{:>10}myDrive = gDrive(service)'.format(''))
            return(None)
        # create the HTTP interface (not entirely sure how this works)
        self.http = object.authorize(httplib2.Http()) 
    
        # build the api discovery service using the http
        self.service = discovery.build('drive', 'v3', http=self.http, cache_discovery=False)
        
        #self.service = object
        # https://developers.google.com/drive/v3/web/mime-types
        self.mimeTypes = {'audio': 'application/vnd.google-apps.audio',
                          'docs': 'application/vnd.google-apps.document',
                          'drawing': 'application/vnd.google-apps.drawing',
                          'file': 'application/vnd.google-apps.file',
                          'folder': 'application/vnd.google-apps.folder',
                          'forms': 'application/vnd.google-apps.form',
                          'mymaps': 'application/vnd.google-apps.map',
                          'photos': 'application/vnd.google-apps.photo',
                          'slides': 'application/vnd.google-apps.presentation',
                          'scripts': 'application/vnd.google-apps.script',
                          'sites': 'application/vnd.google-apps.sites',
                          'sheets': 'application/vnd.google-apps.spreadsheet',
                          'video': 'application/vnd.google-apps.video'}
        
        # fields to include in partial responses
        # https://developers.google.com/apis-explorer/#p/drive/v3/drive.files.create
        self.fields = ['id', 'parents', 'mimeType', 'webViewLink', 'size', 'createdTime', 'trashed', 'kind', 'name']
    
#     types = property()
    
    @property
    def types(self):
        '''
        Display supported mimeTypes
        '''
        print('supported mime types:')
        for key in self.mimeTypes:
            #print('%10s: %s' % (key, self.mimeTypes[key]))
            print('{:8} {val}'.format(key+':', val=self.mimeTypes[key]))
    
#     def quote(self, string):
#         '''
#         add double quotes arounda string
#         '''
#         return('"'+str(string)+'"')
    

    
    def add(self, name = None, mimeType = False, parents = None, 
            fields = 'webViewLink, mimeType, id', sanitize = True):
        '''
        add a file to google drive or team drive:
        NB! when adding to the root of a team drive use the drive ID as the parent

        args:
            name (string): human readable name
            mimeType (string): mimeType (see self.mimeTypes for a complete list)
            parents (list): list of parent folders
            fields (comma separated string): properties to query and return any of the following:
                'parents', 'mimeType', 'webViewLink', 
                'size', 'createdTime', 'trashed'
                'id'
            sanitize (bool): remove any field options that are not in the above list - false to allow anything
            
        '''

        fieldsExpected = self.fields
        fieldsProcessed = []
        fieldsUnknown = []
        
        if sanitize:
            # remove whitespace and unknown options
            for each in fields.replace(' ','').split(','):
                if each in fieldsExpected:
                    fieldsProcessed.append(each)
                else:
                    fieldsUnknown.append(each)
        else:
            fieldsProcessed = fields.split(',')
            
        if len(fieldsUnknown) > 0:
            logging.warn('unrecognized fields: {}'.format(fieldsUnknown))
        
        
        body={}
        if name is None:
            logging.error('expected a folder or file name')
            return(False)
        else:
            body['name'] = name
        
        if mimeType in self.mimeTypes:
            body['mimeType'] = self.mimeTypes[mimeType]
        
        if isinstance(parents, list):
            body['parents'] = parents
        elif parents:
            body['parents'] = [parents]
        
        apiString = 'body={}, fields={}'.format(body, ','.join(fieldsProcessed))
        logging.debug('api call: files().create({})'.format(apiString))
        try:
            result = self.service.files().create(supportsTeamDrives=True, body=body, fields=','.join(fieldsProcessed)).execute()
            return(result)
        except errors.HttpError as e:
            raise GDriveError(e)
            return(False)        
        
    def search(self, name = None, trashed = None, mimeType = False, fuzzy = False, date = None, dopperator = '>', 
               parents = None, orderBy = 'createdTime', teamdrive = None, quiet = True):
        '''
        search for an item by name and other properties in google drive
        
        args:
            name (string): item name in google drive - required
            trashed (bool): item is not in trash - default None (not used)
            mimeType = (string): item is one of the known mime types (gdrive.mimeTypes) - default None
            fuzzy = (bool): substring search of names in drive
            date = (RFC3339 date string): modification time date string (YYYY-MM-DD)
            dopperator (date comparison opprator string): <, >, =, >=, <=  - default >
            parents = (string): google drive file id string
            orderBy = (comma separated string): order results assending by keys below - default createdTime:
                        'createdTime', 'folder', 'modifiedByMeTime', 
                        'modifiedTime', 'name', 'quotaBytesUsed', 
                        'recency', 'sharedWithMeTime', 'starred', 
                        'viewedByMeTime'
            fields (comma separated string): properties to query and return any of the following:
                'parents', 'mimeType', 'webViewLink', 
                'size', 'createdTime', 'trashed'
                'id'
            sanitize (bool): remove any field options that are not in the above list - false to allow anything
            teamdrive (string): Team Drive ID string - when included only the specified Team Drive is searched
            quiet (bool): false prints all the results
                        
                        
            
        returns:
            list of file dict
        '''
        features = ['name', 'trashed', 'mimeType', 'date', 'parents']
        build = {'name' : 'name {} "{}"'.format(('contains' if fuzzy else '='), name),
                 'trashed' : 'trashed={}'. format(trashed),
                 'mimeType' : 'mimeType="{}"'.format(self.mimeTypes[mimeType] if mimeType in self.mimeTypes else ''),
                 'parents': '"{}" in parents'.format(parents),
                 'date': 'modifiedTime{}"{}"'.format(dopperator, date)}


    
            
        # provides for setting trashed to True/False if the input is not None
        if not isinstance(trashed, type(None)):
            # set to true as the variable is now in use, but it's value has been set above
            trashed = True
        
        qList = []

        # evaluate feature options; if they are != None/False, use them in building query
        for each in features:
            if eval(each):
                qList.append(build[each])
                
        if not quiet:
            print(' and '.join(qList))
        
        apiString = 'q={}, orderBy={})'.format(' and '.join(qList), orderBy)
        logging.debug('apicall: files().list({})'.format(apiString))
        try:
            # build a query with "and" statements

            if teamdrive:
                result = self.service.files().list(q=' and '.join(qList), 
                                                   orderBy=orderBy, 
                                                   corpora='teamDrive',
                                                   includeTeamDriveItems='true',
                                                   teamDriveId=teamdrive, 
                                                   supportsTeamDrives='true').execute()
            else:
                result = self.service.files().list(q=' and '.join(qList), orderBy=orderBy).execute()
            return(result)
        except errors.HttpError as e:
            raise GDriveError(e)
            return(False)

    def ls(self, *args, **kwargs):
        '''
        List files in google drive using any of the following properties:
            
        accepts:
            name (string): item name in google drive - required
            trashed (bool): item is not in trash - default None (not used)
            mimeType = (string): item is one of the known mime types (gdrive.mimeTypes) - default None
            fuzzy = (bool): substring search of names in drive
            date = (RFC3339 date string): modification time date string (YYYY-MM-DD)
            dopperator (date comparison opprator string): <, >, =, >=, <=  - default >
            parent = (string): google drive file id string    
        '''
        try:
            result = self.search(*args, **kwargs)
            for eachFile in result.get('files', []):
                print('name: {f[name]}, ID:{f[id]}, mimeType:{f[mimeType]}'.format(f=eachFile))
            return(result)
        except GDriveError as e:
            raise GDriveError(e)
            
    
    
    def getprops(self, fileId = None, fields = 'parents, mimeType, webViewLink', sanitize=True):
        '''
        get a file or folder's properties based on google drive fileId
        
        for a more complete list: https://developers.google.com/drive/v3/web/migration
        
        args:
            fileId (string): google drive file ID
            fields (comma separated string): properties to query and return any of the following:
                'parents', 'mimeType', 'webViewLink', 'size', 'createdTime', 'trashed'
            sanitize (bool): remove any field options that are not in the above list - false to allow anything
            
        returns:
            list of dictionary - google drive file properties
            
        raises GDriveError
        '''
        fieldsExpected = self.fields
        
        fieldsProcessed = []
        fieldsUnknown = []

        if sanitize:
            # remove whitespace and unknown options
            for each in fields.replace(' ','').split(','):
                if each in fieldsExpected:
                    fieldsProcessed.append(each)
                else:
                    fieldsUnknown.append(each)
        else:
            fieldsProcessed = fields.split(',')
        if len(fieldsUnknown) > 0:
            print ('unrecognized fields: {}'.format(fieldsUnknown))
        
        apiString = 'fileId={}, fields={}'.format(fileId, ','.join(fieldsProcessed))
        logging.debug('files().get({})'.format(apiString))
        try:
            result = self.service.files().get(supportsTeamDrives=True, fileId=fileId, fields=','.join(fieldsProcessed)).execute()
            return(result)
        except errors.HttpError as e:
            raise GDriveError(e)
            return(False)
        
    def getpermissions(self, fileID):
        """
        get a file, folder or Team Drive's permissions
        """
        try:
            permissions = self.service.permissions().list(fileId=fileID, 
                                                          supportsTeamDrives=True).execute()
            return permissions
        except errors.HttpError, error:
              print 'An error occurred: %s' % error
        return None
        
    def parents(self, fileId):
        # need to update to work with TeamDrive
        """get a file's parents.

        Args:
            fileId: ID of the file to print parents for.
        
        raises GDriveError
        """
        apiString = 'fileId={}, fields="parents"'.format(fileId)
        logging.debug('api call: {}'.format(apiString))
        try:
            parents = self.service.files().get(supportsTeamDrives=True,fileId=fileId, fields='parents').execute()
            return(parents)
        except errors.HttpError as e:
            raise GDriveError(e)
            return(None)
    
    def rm(self):
        pass
    
    def getuserid(self):
        '''
        get the current user's ID
        '''
        # more info here: https://developers.google.com/apis-explorer/#search/drive.about.get/m/drive/v3/drive.about.get?fields=user&_h=1&
        try:
            uid = self.service.about().get(fields="user/permissionId").execute()
            #return(uid)
            return(uid['user']['permissionId'])
        except errors.HttpError as e:
            raise GDriveError(e)
            return(None)
        
    
    def listTeamDrives(self):
        '''
        List first page of team drives available to the user 
            - this method ignores the continuation token (I can't figure it out!)
            raises GDriveError
            
            returns: 
                dictonary of first page of TeamDrives and capabilities
        '''
        fields = ['teamDrives']
       
        
        try:
            result = self.service.teamdrives().list(fields=','.join(fields)).execute()
            return(result['teamDrives'])
        except errors.HttpError as e:
            raise GDriveError(e)
            return(False)


# In[167]:

# create an instance for testing
# from auth import *
# credential_store = "/tmp/"
# credentials = getCredentials(credential_store)
# myDrive = googledrive(credentials)



