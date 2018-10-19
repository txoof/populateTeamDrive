#!/bin/bash
APPNAME="portfolioCreator"

if [[ "$VIRTUAL_ENV" != "" ]] ; then
  ~/bin/nbconvert "$APPNAME".ipynb
  pyinstaller --clean *.spec
  zip -j /Volumes/GoogleDrive/Team\ Drives/ES\ Student\ Cumulative\ Folders/PortfolioCreator\ Application/portfolioCreator.zip ./dist/portfolioCreator
#  cp ./dist/portfolioCreator /Volumes/GoogleDrive/Team\ Drives/ES\ Student\ Cumulative\ Folders/PortfolioCreator\ Application/
else
  echo "This must be run from within a virtual environment with pyinstaller"
fi
