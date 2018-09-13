#!/usr/bin/env bash
# https://github.com/devernay/cminpack/blob/master/.travis-coverity-scan-build.sh
PLATFORM=`uname`
TOOL_ARCHIVE=/tmp/cov-analysis-${PLATFORM}.tgz
TOOL_URL=https://scan.coverity.com/download/${PLATFORM}
TOOL_BASE=/tmp/coverity-scan-analysis
UPLOAD_URL="http://scan5.coverity.com/cgi-bin/travis_upload.py"


# Verify upload is permitted
permit=true
AUTH_RES=`curl -s --form project="$COVERITY_SCAN_PROJECT_NAME" --form token="$COVERITY_SCAN_TOKEN" $SCAN_URL/api/upload_permitted`
if [ "$AUTH_RES" = "Access denied" ]; then
  echo -e "\033[33;1mCoverity Scan API access denied. Check COVERITY_SCAN_PROJECT_NAME and COVERITY_SCAN_TOKEN.\033[0m"
  exit 1
else
  AUTH=`echo ${AUTH_RES} | ruby -e "require 'rubygems'; require 'json'; puts JSON[STDIN.read]['upload_permitted']"`
  if [ "$AUTH" = "true" ]; then
    echo -e "\033[33;1mCoverity Scan analysis authorized per quota.\033[0m"
  else
    WHEN=`echo ${AUTH_RES} | ruby -e "require 'rubygems'; require 'json'; puts JSON[STDIN.read]['next_upload_permitted_at']"`
    echo -e "\033[33;1mOops!Coverity Scan analysis engine NOT authorized until $WHEN.\033[0m"
    permit=false
  fi


# Download Coverity Scan Analysis Tool
echo -e "\033[33;1mDownloading Coverity Scan Analysis Tool...\033[0m"
wget -nv -O $TOOL_ARCHIVE $TOOL_URL --post-data "project=$COVERITY_SCAN_PROJECT_NAME&token=$COVERITY_SCAN_TOKEN"
# Extract Coverity Scan Analysis Tool
echo -e "\033[33;1mExtracting Coverity Scan Analysis Tool...\033[0m"
mkdir -p ${TOOL_BASE}
pushd ${TOOL_BASE}
tar xzf ${TOOL_ARCHIVE}
popd
TOOL_DIR=`find ${TOOL_BASE} -type d -name 'cov-analysis*'`
export PATH=${TOOL_DIR}/bin:$PATH
# Build
echo -e "\033[33;1mRunning Coverity Scan Analysis Tool...\033[0m"
COV_BUILD_OPTIONS="-no-command --fs-capture-search ./apifuzzer/"
RESULTS_DIR="cov-int"
COVERITY_UNSUPPORTED=1 cov-build --dir $RESULTS_DIR ${COV_BUILD_OPTIONS}

# Upload results
echo -e "\033[33;1mTarring Coverity Scan Analysis results...\033[0m"
RESULTS_ARCHIVE=analysis-results.tgz
tar czf $RESULTS_ARCHIVE $RESULTS_DIR
SHA=`git rev-parse --short HEAD`
#VERSION_SHA=$(cat VERSION)#$SHA

echo -e "\033[33;1mUploading Coverity Scan Analysis results...\033[0m"
response=$(curl \
  --silent --write-out "\n%{http_code}\n" \
  --form project=${COVERITY_SCAN_PROJECT_NAME} \
  --form token=${COVERITY_SCAN_TOKEN} \
  --form email=${COVERITY_SCAN_NOTIFICATION_EMAIL} \
  --form file=@${RESULTS_ARCHIVE} \
  --form version=${SHA} \
  --form description="Travis CI build" \
  ${UPLOAD_URL})
status_code=$(echo "$response" | sed -n '$p')
if [ "$status_code" != "201" ]; then
  TEXT=$(echo "$response" | sed '$d')
  echo -e "\033[33;1mCoverity Scan upload failed: $TEXT.\033[0m"
  exit 1
fi
