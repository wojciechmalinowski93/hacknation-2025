@echo off
echo Starting script...

echo Step 1: Doing something...
rem This is a comment line
echo Done with step 1.

echo Step 2: Pausing for 2 seconds...
timeout /t 2 > nul

echo Step 3: Listing files in current directory:
dir

echo Step 4: Changing directory to C:\
cd C:\

echo Step 5: Creating a folder named TempTest
mkdir TempTest

echo Step 6: Navigating into TempTest
cd TempTest

echo Step 7: Creating a test file
echo This is a test file. > test.txt

echo Step 8: Displaying the contents of test.txt
type test.txt

echo Step 9: Deleting the test file
del test.txt

echo Step 10: Going back one level up
cd ..

echo Step 11: Deleting the TempTest folder
rmdir TempTest

echo Script complete.
pause