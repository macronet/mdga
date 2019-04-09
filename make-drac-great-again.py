#!/usr/bin/python
'''Requires firmware upgrade files to be available under <chassis>/<file> -structure'''
import sys, getopt
import getpass
# pexpect is needed for logging interactively(hide password from command line) into a DRAC
import pexpect
from time import sleep

arguments = sys.argv[1:]
passwordfile = ''

sysinfo = ''
chassis = ''
chassis_supported = ['R620','R630','R640']
dracuser = 'root'
dracpass = ''
dracip = ''
dracversion = ''
dracmajor = ''
dracminor = ''
draclist = []
dracupgradeversion = ''

R620_DRAC_versions = [
    ['2.61.60.60','iDRAC-with-Lifecycle-Controller_Firmware_VYGMM_WN64_2.61.60.60_A00_02.EXE'],
    ['2.41.40.40','iDRAC-with-Lifecycle-Controller_Firmware_XTPX4_WN64_2.41.40.40_A00.EXE'],
    ['2.30.30.30','iDRAC-with-Lifecycle-Controller_Firmware_JHF76_WN64_2.30.30.30_A00.EXE'],
    ['2.21.21.21','iDRAC-with-Lifecycle-Controller_Firmware_VV01T_WN64_2.21.21.21_A00.EXE'],
    ['2.10.10.10','iDRAC-with-Lifecycle-Controller_Firmware_Y5K20_WN32_2.10.10.10_A00.EXE'],
    ['1.66.65','ESM_Firmware_3F4WV_WN64_1.66.65_A00.EXE']
    ]
R630_DRAC_versions = [
    ['2.61.60.60','iDRAC-with-Lifecycle-Controller_Firmware_1HY5M_WN32_2.61.60.60_A00_02.EXE'],
    ['2.41.40.40','iDRAC-with-Lifecycle-Controller_Firmware_4950Y_WN32_2.41.40.40_A00.EXE'],
    ['2.30.30.30','iDRAC-with-Lifecycle-Controller_Firmware_5GCHC_WN32_2.30.30.30_A00.EXE'],
    ['2.21.21.21','iDRAC-with-Lifecycle-Controller_Firmware_1X82C_WN64_2.21.21.21_A00.EXE'],
    ['2.10.10.10','iDRAC-with-Lifecycle-Controller_Firmware_FM1PC_WN64_2.10.10.10_A00.EXE']
    ]
R640_DRAC_versions = [
    ['3.30.30.30','iDRAC-with-Lifecycle-Controller_Firmware_G6W0W_WN64_3.30.30.30_A00.EXE'],
    ['3.21.21.21','iDRAC-with-Lifecycle-Controller_Firmware_387FW_WN64_3.21.21.21_A00.EXE']
    ]

try:
    opts, args = getopt.getopt(arguments,"d:p:")
except getopt.GetoptError:
    print('.py -d <DRAC IP> -p <read password from file (optional)>')
    sys.exit(2)
for opt, arg in opts:
    if opt == '-d':
        dracip = arg
    elif opt == '-p':
        passwordfile = './' + arg
        with open(passwordfile) as f:
            dracpass = f.readline()

if(dracip == ''):
    print ('.py -d <DRAC IP> -p <read password from file (optional)>')
    sys.exit(2)
if(dracpass == ''):
    dracpass = getpass.getpass(prompt='DRAC password:')

def drac_sysinfo_update(ip,dracuser,dracpass):
    print('/opt/dell/srvadmin/bin/idracadm7 -r ' + ip + ' -i getsysinfo')
    child = pexpect.spawn('/opt/dell/srvadmin/bin/idracadm7 -r ' + ip + ' -i getsysinfo',timeout=300)
    child.expect('UserName: ')
    child.sendline(dracuser)
    child.expect('Password: ')
    child.sendline(dracpass)
    child.expect('Embedded NIC MAC Addresses:')
    return(child.before)

def drac_check_next_upgrade(draclist,dracversion):
    print('Current DRAC firmware: '+ dracversion)
    dracupgradeversion=''
    i = 0
    draclist.sort(reverse = True)
    # Hardcoded upgrade path for v1 -> v2
    if dracmajor == '1':
        if dracminor >= '66':
            dracupgradeversion = 'iDRAC-with-Lifecycle-Controller_Firmware_Y5K20_WN32_2.10.10.10_A00.EXE'
        else:
            dracupgradeversion = 'ESM_Firmware_3F4WV_WN64_1.66.65_A00.EXE'
    if dracmajor == '2':
        while i < len(draclist):
            print('Check upgrade to ' + draclist[i][0])
            if dracversion < draclist[i][0]:
                dracupgradeversion = draclist[i][1]
                print('Newer, selected ' + draclist[i][0])
            i += 1
    if dracmajor == '3':
        while i < len(draclist):
            print('Check upgrade to ' + draclist[i][0])
            if dracversion < draclist[i][0]:
                dracupgradeversion = draclist[i][1]
                print('Newer, selected ' + draclist[i][0])
            i += 1
    if dracupgradeversion == '':
        print('Already up-to-date (or not supported by script).')
        sys.exit(0)
    return(dracupgradeversion)

if chassis in chassis_supported:
    print(chassis + ' is supported for updates.')
    draclist = globals()[chassis + '_DRAC_versions']
    dracupgradeversion = drac_check_next_upgrade(draclist,dracversion)
else:
    print(chassis + ' is not supported for updates.')

def drac_upgrade(ip,dracuser,dracpass,dracupgradeversion):
    print('Using ' + dracupgradeversion + ' - this will take about 30-60mins.')
    print('/opt/dell/srvadmin/bin/idracadm7 -r ' + ip + ' -i update -f ./' + chassis + '/' + dracupgradeversion)
    child = pexpect.spawn('/opt/dell/srvadmin/bin/idracadm7 -r ' + ip + ' -i update -f ./' + chassis + '/' + dracupgradeversion,timeout=7200)
    child.delaybeforesend = 1
    child.expect('UserName:')
    child.sendline(dracuser)
    child.expect('Password:')
    child.sendline(dracpass)
    child.expect(pexpect.EOF)
    #child.expect('To reboot the system  manually, use the "racadm serveraction powercycle" command.')
    return True

while True:
    sysinfo = drac_sysinfo_update(dracip,dracuser,dracpass)
    biosversion = [line for line in sysinfo.split('\n') if "System BIOS Version" in line][-1].split()[-1]
    chassis = [line for line in sysinfo.split('\n') if "System Model" in line][-1].split()[-1]
    dracversion = [line for line in sysinfo.split('\n') if "Firmware Version" in line][-1].split()[-1]
    print('We are dealing with a ' + chassis + ', BIOS version ' + biosversion + ' and DRAC firmware ' + dracversion)
    dracmajor = dracversion.split(".")[0]
    dracminor = dracversion.split(".")[1]
    drac_check_next_upgrade(draclist,dracversion)
    drac_upgrade(dracip,dracuser,dracpass,dracupgradeversion)
    # Let DRAC settle for 10 minutes after upgrade
    sleep(600)