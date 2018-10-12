#!/bin/bash
if [[ "$VIRTUAL_ENV" != "" ]] ; then
  pyinstaller --clean *.spec
  cp ./dist/portfolioCreator /Volumes/GoogleDrive/Team\ Drives/ES\ Student\ Cumulative\ Folders/PortfolioCreator\ Application/
else
  echo "This must be run from within a virtual environment with pyinstaller"
fi
