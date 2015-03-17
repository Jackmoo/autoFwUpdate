#!/usr/bin/env python
# -*- coding: utf-8 -*-
#====================================================
# environment: python 2.7
# required externale module: pexpect
# author: Jack Chung
#====================================================

import sys
import subprocess
import readline
import pexpect
import time

#======== config variable ==========
NAS_IP = ""
NAS_name = ""
mount_remote_folder = "192.168.76.211:/Firmware_Release/ES_daily_build/"
NAS_account = ""
NAS_password = ""
IS_REINIT = False
sshNewKey = "Are you sure you want to continue connecting"
updateDailyType = ""
updateFwName = ""
updateFwPath = ""
updateBothController = True

cmdSearchLatest = 'find . -name *.fw -type f -print0 | xargs -0 stat -f "%m %N" | sort -rn | head -1 | cut -f2- -d" "'
cmdSearchLatestDAILY = 'find -E . -name *.fw -type f -regex ".+(4200).+(DAILY).+"  -print0 | xargs -0 stat -f "%m %N" | sort -rn | head -1 | cut -f2- -d" "'

#===================================

#======== local function ===========
def createSshSession (IP, account, passwd):
    cmd = "ssh " + account + "@" + IP
    p = pexpect.spawn(cmd, timeout=10)
    i = p.expect(["Are you sure you want to continue connecting",'password:',pexpect.EOF,'# '])
    if i==0:
        print "I say yes"
        p.sendline('yes')
        i=p.expect(["Are you sure you want to continue connecting",'password:',pexpect.EOF,'# '])
    if i==1:
        print "I give password",
        p.sendline(passwd)
        p.expect([pexpect.EOF,'# '])
    elif i==2:
        print "I either got key or connection timeout"
        pass
    elif i==3:
        print "I enter the console"
        pass
    return p
    
def isHostSshAvailable (IP, account):
    print 'connecting to '+IP+'....'
    try:
        p = pexpect.spawn("ssh " + account + "@" + IP, timeout=10)
        p.expect(["Are you sure you want to continue connecting",'password:'])
        return True
    except pexpect.TIMEOUT:
        print 'pexpect timeout'
        return False
    except pexpect.EOF:
        print 'pexpect EOF'
        return False
    except pexpect.ExceptionPexpect:
        print 'something bad happened'
        return False
        
def waitForHostAvailable (IP, account):
    #try connect to another host
    while not isHostSshAvailable(IP, account):
        time.sleep(10)  
    print 'host NOW available!'

def removeTargetSshKey (IP):
    print 'reinit ssh key....'
    sshKeyRemoveCmd = "ssh-keygen -R "+IP
    subprocess.call(sshKeyRemoveCmd, shell=True)
    
#===================================

#=========== main script ===========
cmd = ""

print("Enter the host ip/domain you want to update")
NAS_IP = raw_input('')
print NAS_IP
print("Enter the host login information")
NAS_account = raw_input('account: ')
print NAS_account
NAS_password = raw_input('password: ')
print NAS_password

#since after reinit, the ssh may change, we have to remove it in system 
removeTargetSshKey(NAS_IP)

print("Choose the function you want to perform:\n1)Update firmware ONLY\n2)Reinit NAS ONLY *WARNING* ALL DATA WOULD BE LOST\n3)Do both of above")
taskToDo = raw_input('Please choose(default is 1):')
if taskToDo == '2':
    IS_UPDATE = False
    IS_REINIT = True
elif taskToDo == '3':
    IS_UPDATE = True
    IS_REINIT = True
else:
    IS_UPDATE = True
    IS_REINIT = False
    
#======================== func select & param input =====================
# fw update type
if IS_UPDATE:
    print("choose: \n(1)update latest DAILY firmware \n(2)update any latest firmware \n(3)specify the firmware name \n(4)specify fw with path under 192.168.76.211:/Firmware_Release/ES_daily_build/")
    updateDailyType = raw_input('Please choose(default is 1)')
    if updateDailyType == "1":
        print 'DAILY chose'
    elif updateDailyType == "2":
        print 'any latest chose'
    elif updateDailyType == "3":
        updateFwName = raw_input('enter the specific firmware name: ')
    elif updateDailyType == "4":
        updateFwPath = raw_input('enter the specific firmware with path(e.g.: /2014/Dec/25/ES-4200-4.0.0-343-DAILY-1225-1.fw): ')
    else:
        updateDailyType = "1"
        #updateDailyType = "4"
        #updateFwPath = raw_input('enter the specific firmware with path(e.g.: /2014/Dec/25/ES-4200-4.0.0-343-DAILY-1225-1.fw): ')

# reinit NAS name
if IS_REINIT:
    #get nas name
    print("Please enter the new NAS name you want to set")
    NAS_name = raw_input('')

# update both controller (es4200, x80)    
print("Update both controller? (y/N) (Default: yes)")
updateBoth = raw_input('')
print updateBoth
if updateBoth is 'N':
    updateBothController = False
   
print "login information"
print "IP: "+NAS_IP
print "account: "+NAS_account
print "password: "+NAS_password
print "WORK to do:"
print "update firmware: "+str(IS_UPDATE)
print "update method: "+updateDailyType
print "update both controller: "+updateBoth
print "reinit: "+str(IS_REINIT)
print "new NAS name: "+NAS_name

print("\n***FINAL CHECK*** Are you sure you want to do above task?(y/N)")
FINAL_CEHCK = raw_input('')
if not FINAL_CEHCK=='y':
    print "Abort...."
    sys.exit()
    
#============================ main script ======================================    
if IS_UPDATE:
    #try connect to another host
    waitForHostAvailable(NAS_IP, NAS_account)

    try:
        sshProcess = createSshSession(NAS_IP, NAS_account, NAS_password)
        print 'successfully login ssh'
    except pexpect.ExceptionPexpect:
        print 'failed to login ssh'
        sys.exit()

    # make folder for mount 
    sshProcess.sendline('mkdir /mnt/fwupdate')
    sshProcess.expect('# ')
    print sshProcess.before 

    # check if already mounted
    sshProcess.sendline("df | grep ``" + mount_remote_folder[:15]+"''")
    sshProcess.expect('# ')
    dfResult = sshProcess.before
    if dfResult.find('/Firmware_Release/ES_daily_build/') == -1:
        # mount remote folder where daily build is
        sshProcess.sendline('mount -o tcp '+mount_remote_folder+' /mnt/fwupdate/')
        sshProcess.expect('# ',timeout=60)    #increase timeout that sometimes mount remote folder cause some delay
        
    print sshProcess.before
    # send command to check firmware location
    sshProcess.sendline('cd /mnt/fwupdate')
    sshProcess.expect('# ')
    if updateDailyType == '1':
        sshProcess.sendline(cmdSearchLatestDAILY)
    elif updateDailyType == '2':
        sshProcess.sendline(cmdSearchLatest)
    elif updateDailyType == '3':
        cmdSpecificFw = 'find . -type f -name '+updateFwName+' -print0 | xargs -0 stat -f "%m %N" | sort -rn | head -1 | cut -f2- -d" "'
        sshProcess.sendline(cmdSpecificFw)
    else:
        #default, latest DAILY
        sshProcess.sendline(cmdSearchLatestDAILY)
    #sshProcess.expect('" "', timeout=120)
    sshProcess.expect('.fw\r\n', timeout=120)  #since the search takes long time, timeout set to 2min
    if updateDailyType == '4':
        absoluteUpdateFwPath = '/mnt/fwupdate'+updateFwPath
    else:
        updateFwPath = sshProcess.before.splitlines()[-1]
        absoluteUpdateFwPath = '/mnt/fwupdate'+updateFwPath[1:]+'.fw' # remove '.', add /mnt/fwupdate
    print('===================================')
    print(absoluteUpdateFwPath)
    print('===================================')

    #update fw
    print 'updating fw....'
    if updateBothController:
        print '/nas/util/fwupdate -nNp -s local '+absoluteUpdateFwPath
        sshProcess.sendline('/nas/util/fwupdate -nNp -s local '+absoluteUpdateFwPath)
    else:
        print '/nas/util/fwupdate -nN -s local '+absoluteUpdateFwPath
        sshProcess.sendline('/nas/util/fwupdate -nN -s local '+absoluteUpdateFwPath)
    updateResult = sshProcess.expect(['Firmware update successfully.','Firmware update failed'], timeout=360)
    print sshProcess.before
    if updateResult==0:
        print '===update SUCCESS!===' 
    elif updateResult==1:
        print '===update FAILED!, exiting script...===' 
        sys.exit()

    #reboot the system
    sshProcess.expect('# ')
    time.sleep(30)  #wait for another controller to complete fw update 
    sshProcess.sendline('cf reboot')
    print 'rebooting...'
    time.sleep(5) 
    sshProcess.terminate()
    print 'ssh close' # print out the result
    time.sleep(60) 
        
    #try connect to another host
    removeTargetSshKey(NAS_IP)
    waitForHostAvailable(NAS_IP, NAS_account)

if IS_REINIT:
    #if reinit, do '/nas/util/qsector write - 7 0', reboot, do'/nas/util/cfsetup -bcy es4200 <hostname>'  
    #try connect to another host

    #since after reinit, the ssh may change, we have to remove it in system 
    removeTargetSshKey(NAS_IP)
    
    waitForHostAvailable(NAS_IP, NAS_account)
    
    #qsector
    try:
        initProcess = createSshSession(NAS_IP, NAS_account, NAS_password)
        print 'successfully login ssh'
    except pexpect.ExceptionPexpect:
        print 'failed to login ssh'
    print 'erasing qsector...'
    initProcess.sendline('/nas/util/qsector write - 7 0')
    initProcess.expect(['# ',pexpect.EOF])
    time.sleep(5)

    #reboot
    initProcess.sendline('cf reboot')
    print 'rebooting...'
    time.sleep(5) 
    initProcess.terminate()
    print 'ssh close' # print out the result
    time.sleep(240)

    #since after reinit, the ssh may change, we have to remove it in system 
    removeTargetSshKey(NAS_IP)
    
    #try connect to another host
    waitForHostAvailable(NAS_IP, NAS_account)
    
    
    #cfsetup
    try:
        setupProcess = createSshSession(NAS_IP, NAS_account, NAS_password)
        print 'successfully login ssh'
    except pexpect.ExceptionPexpect:
        print 'failed to login ssh'
    time.sleep(3)
    print setupProcess.before
    setupProcess.sendline('\n')
    setupProcess.sendline('/nas/util/cfsetup es4200 -b -c -y '+NAS_name)
    print '/nas/util/cfsetup es4200 -b -c -y '+NAS_name
    setupProcess.expect('qess.cf.initialized=1',timeout=120)
    print 'cfsetup should be okay, check if rebooting'
    setupProcess.expect('# ',timeout=120)
    print setupProcess.before
    
    time.sleep(240)
    removeTargetSshKey(NAS_IP)
    waitForHostAvailable(NAS_IP, NAS_account)

print "================================================================"
print "                   autoFwUpdate script ENDs                     "
print "================================================================"
sys.exit()
