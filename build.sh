#!/bin/bash
APPNAME="portfolioCreator"
DATESTR=`date +%F_%H.%M`
FNAME="$APPNAME-$DATESTR.zip"
LNAME="$APPNAME-latest.zip"


pipenv run  pyinstaller --clean *.spec
zip -j $FNAME ./dist/portfolioCreator
cp  $FNAME $LNAME

git add $FNAME $LNAME
git commit -m "update build" $FNAME $LNAME
git push


#mv /Volumes/GoogleDrive/Shared\ drives/ASH\ Student\ Cumulative\ Folders/PortfolioCreator\ Application/*.zip /Volumes/GoogleDrive/Team\ Drives/ASH\ Student\ Cumulative\ Folders/PortfolioCreator\ Application/Old\ Versions

#zip -j /Volumes/GoogleDrive/Team\ Drives/ASH\ Student\ Cumulative\ Folders/PortfolioCreator\ Application/portfolioCreator_$DATESTR.zip ./dist/portfolioCreator

