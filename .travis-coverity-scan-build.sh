#!/usr/bin/env bash
# https://github.com/devernay/cminpack/blob/master/.travis-coverity-scan-build.sh
PLATFORM=`uname`
TOOL_ARCHIVE=/tmp/cov-analysis-${PLATFORM}.tgz
TOOL_URL=https://scan.coverity.com/download/${PLATFORM}
TOOL_BASE=/tmp/coverity-scan-analysis
UPLOAD_URL="http://scan5.coverity.com/cgi-bin/travis_upload.py"
SCAN_URL="https://scan.coverity.com"

# Download Coverity Scan Analysis Tool
echo -e "\033[33;1mDownloading Coverity Scan Analysis Tool...\033[0m"
wget -nv -O $TOOL_ARCHIVE $TOOL_URL --post-data "project=$COVERITY_SCAN_PROJECT_NAME&token=$COVERITY_SCAN_TOKEN"
# Extract Coverity Scan Analysis Tool
echo -e "\033[33;1mExtracting Coverity Scan Analysis Tool...\033[0m"
mkdir -p $TOOL_BASE
pushd $TOOL_BASE
tar xzf $TOOL_ARCHIVE
popd
TOOL_DIR=`find $TOOL_BASE -type d -name 'cov-analysis*'`
export PATH=$TOOL_DIR/bin:$PATH
# Build
echo -e "\033[33;1mRunning Coverity Scan Analysis Tool...\033[0m"
COV_BUILD_OPTIONS="-no-command --fs-capture-search ./apifuzzer/"
RESULTS_DIR="cov-int"
COVERITY_UNSUPPORTED=1 cov-build --dir $RESULTS_DIR $COV_BUILD_OPTIONS

# Upload results
echo -e "\033[33;1mTarring Coverity Scan Analysis results...\033[0m"
RESULTS_ARCHIVE=analysis-results.tgz
tar czf $RESULTS_ARCHIVE $RESULTS_DIR
SHA=`git rev-parse --short HEAD`
#VERSION_SHA=$(cat VERSION)#$SHA

echo -e "\033[33;1mUploading Coverity Scan Analysis results...\033[0m"
curl \
  --progress-bar \
  --form project=$COVERITY_SCAN_PROJECT_NAME \
  --form token=$COVERITY_SCAN_TOKEN \
  --form email=$COVERITY_SCAN_NOTIFICATION_EMAIL \
  --form file=@$RESULTS_ARCHIVE \
  --form version=$SHA \
  --form description="Travis CI build" \
  $UPLOAD_URL
