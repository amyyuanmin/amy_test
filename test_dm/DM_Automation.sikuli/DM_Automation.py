import os
import sys
from datetime import timedelta
from datetime import datetime
def FindRecentFolder(folder):
    lists = os.listdir(folder)  #List all folder in protocol directories and return the list.
    test_dir = folder
    print("test dir is {}".format(test_dir))
    lists.sort(key=lambda fn:os.path.getmtime(test_dir + '\\' + fn)) #According time to sort the element in lists.
    file_path = os.path.join(test_dir, lists[-1])
    return file_path
doubleClick("1553678989981.png")
wait(10)

doubleClick("1529478806503.png")
wait("1553673202367.png")
click(Pattern("1553767862084.png").similar(0.90))
click("1553673303704.png")
exists("1553738677820.png")
doubleClick("1529478916341.png")
T2_folder = sys.argv[1]
T3_folder = sys.argv[2]

wait(180)
T2_recent_folder = FindRecentFolder(T2_folder)
print("T2 recent folder is {}".format(T2_recent_folder)) 
T2_wait_until = datetime.now() + timedelta(hours=int(3))  
while 1:
    if len(os.listdir(T2_recent_folder)) >= 30:
        print(len(os.listdir(T2_recent_folder)))
        break
    elif T2_wait_until < datetime.now():
        print("timeout")
        break
wait(180)
T3_recent_folder = FindRecentFolder(T3_folder)
print("T3 recent folder is {}".format(T3_recent_folder))
T3_wait_until = datetime.now() + timedelta(hours=int(5))  
while 1:
    if len(os.listdir(T3_recent_folder)) >= 34:
        print(len(os.listdir(T3_recent_folder)))
        break
    elif T3_wait_until < datetime.now():
        print("timeout")
        break