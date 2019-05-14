#!/usr/bin/python
'''Requires firmware upgrade files to be available under <chassis>/<file> -structure'''
'''v1 & v2 pre 2.21.21.21: max path length 64 characters'''
import sys, getopt
import getpass
# pexpect is needed for logging interactively(hide password from command line) into a DRAC
import pexpect
from time import sleep

chassis_supported = ['R620','R720xd','R630','R730xd','R640']
drac_user = 'root'

R620_BIOS_versions = [
    ['2.7.0','BIOS_NGYCX_WN64_2.7.0_01.EXE']
    ]
R720xd_BIOS_versions = [
    ['2.7.0','BIOS_DYH8T_WN64_2.7.0_01.EXE']
    ]
R630_BIOS_versions = [
    ['2.9.1','BIOS_T9YX9_WN64_2.9.1.EXE']
    ]
R730xd_BIOS_versions = [
    ['2.9.1','BIOS_T9YX9_WN64_2.9.1.EXE']
    ]
R640_BIOS_versions = [
    ['2.1.8','BIOS_DVH2J_WN64_2.1.8.EXE']
    ]

def drac_sysinfo_update(ip, drac_user, drac_pass):
    child = pexpect.spawn('/opt/dell/srvadmin/bin/idracadm7 -r ' + ip + ' --nocertwarn -i getsysinfo', timeout=300)
    child.expect('UserName: ')
    child.sendline(drac_user)
    child.expect('Password: ')
    child.sendline(drac_pass)
    child.expect(pexpect.EOF)
    return(child.before)

def split_bios_version(version):
    return version.split('.')

def is_superior_version(ver1, ver2):
    version1 = split_bios_version(ver1)
    version2 = split_bios_version(ver2)

    # Going through semantic versioning
    for sem1 in version1:
        sem2 = version2[version1.index(sem1)]
        if sem1 == sem2:
            continue
        else:
            if int(sem1) > int(sem2):
                return True
            else:
                return False
    
    # Versions are an exact match
    return False

def bios_check_next_upgrade(bios_list, bios_version):
    print('Current BIOS version: '+ bios_version)

    bios_upgrade_version=''
    bios_list.sort()
    
    for i in bios_list:
        print('Check upgrade to ' + i[0])
        if is_superior_version(i[0], bios_version):
            bios_upgrade_version = i[1]
            print('Newer, selected ' + i[0])
            return bios_upgrade_version
    if bios_upgrade_version == '':
        print('Version ' + bios_version + ' already up-to-date (or not supported by script).')
        sys.exit(0)
    return bios_upgrade_version

def bios_upgrade(chassis, ip, drac_user, drac_pass, bios_upgrade_version):
    print('Using ' + bios_upgrade_version + ' - this will take about 15 minutes.')
    child = pexpect.spawn('/opt/dell/srvadmin/bin/idracadm7 -r ' + ip + ' --nocertwarn -i update -f ./' + chassis + '/' + bios_upgrade_version,timeout=7200)
    child.delaybeforesend = 1
    child.expect('UserName:')
    child.sendline(drac_user)
    child.expect('Password:')
    child.sendline(drac_pass)
    child.expect(pexpect.EOF)
    print(child.before)
    print('Server has to be restarted to update BIOS.')
    return True

def drac_jobqueue_update(ip, drac_user, drac_pass):
    child = pexpect.spawn('/opt/dell/srvadmin/bin/idracadm7 -r ' + ip + ' --nocertwarn -i jobqueue view', timeout=300)
    child.expect('UserName: ')
    child.sendline(drac_user)
    child.expect('Password: ')
    child.sendline(drac_pass)
    child.expect(pexpect.EOF)
    return(child.before)

def main():
    arguments = sys.argv[1:]
    drac_pass = ''
    drac_ip = ''

    try:
        opts, _ = getopt.getopt(arguments,"d:p:")
    except getopt.GetoptError:
        print('Usage:', sys.argv[0], '-d <DRAC IP> -p <read password from file (optional)>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-d':
            drac_ip = arg
        elif opt == '-p':
            password_file = arg
            with open(password_file) as f:
                drac_pass = f.readline()

    if(drac_ip == ''):
        print('Usage: ' + sys.argv[0] + ' -d <DRAC IP> -p <read password from file (optional)>')
        sys.exit(2)
    if(drac_pass == ''):
        drac_pass = getpass.getpass(prompt='DRAC password:')
    
    sysinfo = drac_sysinfo_update(drac_ip, drac_user, drac_pass)
    bios_version = [line for line in sysinfo.split('\n') if "System BIOS Version" in line][-1].split()[-1]
    chassis = [line for line in sysinfo.split('\n') if "System Model" in line][-1].split()[-1]
    drac_version = [line for line in sysinfo.split('\n') if "Firmware Version" in line][-1].split()[-1]
        
    if chassis in chassis_supported:
        print(chassis + ' is supported for updates.')
        if chassis == 'R640':
            jobqueue = drac_jobqueue_update(drac_ip, drac_user, drac_pass)
            if jobqueue.find('Status=Scheduled') != -1:
                print('Update already scheduled, abort.')
                sys.exit(1)
        else:
            #12G/13G remote jobqueue view is crap/broken/licenced
            print('12G/13G Dell, cannot check if update is already scheduled, push update and hope for the best.')
        bios_list = globals()[chassis + '_BIOS_versions']
        bios_upgrade_version = bios_check_next_upgrade(bios_list, bios_version)
    else:
        print(chassis + ' is not supported for updates.')
        sys.exit(1)
        
    print('We are dealing with a ' + chassis + ', BIOS version ' + bios_version + ' and DRAC firmware ' + drac_version)
                
    bios_upgrade(chassis, drac_ip, drac_user, drac_pass, bios_upgrade_version)
    sys.exit(0)

if __name__ == "__main__":
    main()