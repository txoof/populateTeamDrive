portfolioCreator
======
The portfolio creator script creates an empty set of folders for students on Google Team Drive using the [Google Drive REST API V3](https://developers.google.com/drive/api/v3/reference/) using OAuth authentication via a local web browser.

The project depends on credentials (client_secrets.json) file tied to a particular google drive account. Should the included client_secrets.json stop working, a new secret can be generated using the instructions below from any Google Suite (formerly Google Apps for Education) account.

[Using OAuth 2.0 for Installed Applications](https://developers.google.com/api-client-library/python/auth/installed-app)

Building
--------
### Requirements
Required python modules or 
- pyinstaller==3.2.1
- humanfriendly==4.16.1
- httplib2==0.10.3
- google_api_python_client==1.7.4
- progressbar2==3.38.

### Instructions
To build a single-file version of the application that can be run from  the command line or from OS X Finder use:
`$ pyinstaller --clean portfolioCreator.spec`

Specifications
--------------
The script creates portfolio folders using in the following format on a google Team Drive in the following format from Preschool through Grade 12 (inclusive):
```
Portfolio Folder
│
└───Class Of-2001
    |
    └───Lastname, Firstname - 000000
        |
        └───00-Preschool
        |
        └───00-Transition Kindergarten
        |
        └───00-zKindergarten  #z forces the sort to work properly
        |
        └───01-Grade
        |
        └───02-Grade
        |
        └───03-Grade
        |
        └───12-Grade
```
The namming of the grade-level folders is controlled by ./resources/gradefolders.txt. An alternative format can be specified in the configuration file (see configuration section).
The gradefolders.txt file must have one single folder title per line. Trailing whitespace will be stripped
```
00-Preschool
00-Transition Kindergarten
00-zKindergarten
01-Grade
02-Grade
03-Grade
04-Grade
05-Grade
06-Grade
07-Grade
08-Grade
09-Grade
10-Grade
11-Grade
12-Grade
```
Configuration
-------------
Configuration is controlled by ~/.config/portfolioCreator/portfolioCreator.ini using the typical 'ini' format. The configuration will be generated the first time the application is run.
The configuration can (and should) be updated during the execution of the program, but can also be managed here
```
[Main] # main section - this MUST be included
# path to credentials created through the OAuth 2.0 process
credentials = ~/.config/portfolio_creator/credentials/ 

# Team Drive: human readable name
teamdrivename = IT Blabla 
# Team Drive: resource ID - Provided for reference, it does NOT control the folder used
teamdriveid = 0ACLfU8KeD_BHUk9PVA
# Team Drive: folder name - Provided for reference, it does NOT control the folder used
foldername = Port Wine 
# Team Drive: folder ID
folderid = 1-D7UNBes_skfkQ6oBettiBICiBcZmbvn 

# authenicated user - Provided for reference, it does NOT control the authenticated user
useremail = aciuffo@ash.nl 

# Log level DEBUG, INFO, WARN, ERROR, CRITICAL
loglevel = ERROR 

# Optional Alternative gradefolders.txt
gradefolders = /path/to/alternative/gradefolders.txt
```
