#!/usr/bin/python
'''Requires firmware upgrade files to be available under <chassis>/<file> -structure'''
'''v1 & v2 pre 2.21.21.21: max path length 64 characters'''
import sys, getopt, os
import getpass
# pexpect is needed for logging interactively(hide password from command line) into a DRAC
import pexpect
from time import sleep

chassis_supported = ['R620','R720xd','R630','R730xd','R640','R6525']
drac_user = 'root'

for chassis in chassis_supported:
    globals()[chassis + '_DRAC_versions'] = []
    files = os.listdir(chassis)
    updates = []
    for file in files:
        if 'iDRAC' in file:
            updates.append(file)
    
    for update in updates:
        data = []
        haystack = update.removesuffix('.EXE').split("_")
        for needle in haystack:
            if needle[0].isdigit():
                if '.' in needle:
                    data.append(needle)
                    data.append(update)
        globals()[chassis + '_DRAC_versions'].append(data)
    globals()[chassis + '_DRAC_versions'].sort()

def drac_sysinfo_update(ip, drac_user, drac_pass):
    child = pexpect.spawn('/opt/dell/srvadmin/bin/idracadm7 -r ' + ip + ' --nocertwarn -i getsysinfo', timeout=300)
    child.expect('UserName: ')
    child.sendline(drac_user)
    child.expect('Password: ')
    child.sendline(drac_pass)
    child.expect(pexpect.EOF)
    return(child.before)

def split_drac_version(version):
    return version.split('.')

def is_superior_version(ver1, ver2):
    version1 = split_drac_version(ver1)
    version2 = split_drac_version(ver2)

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

def drac_check_next_upgrade(drac_list, drac_version):
    print('Current DRAC firmware: '+ drac_version)

    version_list = split_drac_version(drac_version)
    drac_major = version_list[0]
    drac_minor = version_list[1]

    drac_upgrade_version=''
    drac_list.sort()
    
    if '20' in chassis and drac_major == '1': # Hardcoded upgrade path for v1 -> v2 (for 12G)
        if drac_minor >= '66':
            drac_upgrade_version = 'iDRAC-with-LCC_Y5K20_WN32_2.10.10.10_A00.EXE'
        else:
            drac_upgrade_version = 'ESM_Firmware_3F4WV_WN64_1.66.65_A00.EXE'
    elif drac_major >= '1':
        for i in drac_list:
            print('Check upgrade to ' + i[0])
            if is_superior_version(i[0], drac_version):
                drac_upgrade_version = i[1]
                print('Newer, selected ' + i[0])
                return drac_upgrade_version
    if drac_upgrade_version == '':
        print('Version ' + drac_version + ' already up-to-date (or not supported by script).')
        sys.exit(0)
    return drac_upgrade_version


def drac_upgrade(chassis, ip, drac_user, drac_pass, drac_upgrade_version):
    print('Using ' + drac_upgrade_version + ' - this will take about 30-60mins.')
    child = pexpect.spawn('/opt/dell/srvadmin/bin/idracadm7 -r ' + ip + ' --nocertwarn -i update -f ./' + chassis + '/' + drac_upgrade_version,timeout=7200)
    child.delaybeforesend = 1
    child.expect('UserName:')
    child.sendline(drac_user)
    child.expect('Password:')
    child.sendline(drac_pass)
    child.expect(pexpect.EOF)
    print(child.before)
    return True

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
        print('Usage:', sys.argv[0], '-d <DRAC IP> -p <read password from file (optional)>')
        sys.exit(2)
    if(drac_pass == ''):
        drac_pass = getpass.getpass(prompt='DRAC password:')
    
    while True:
        sysinfo = drac_sysinfo_update(drac_ip, drac_user, drac_pass).decode()
        bios_version = [line for line in sysinfo.split('\n') if "System BIOS Version" in line][-1].split()[-1]
        chassis = [line for line in sysinfo.split('\n') if "System Model" in line][-1].split()[-1]
        drac_version = [line for line in sysinfo.split('\n') if "Firmware Version" in line][-1].split()[-1]
        
        if chassis in chassis_supported:
            print(chassis + ' is supported for updates.')
            drac_list = globals()[chassis + '_DRAC_versions']
            drac_upgrade_version = drac_check_next_upgrade(drac_list, drac_version)
        else:
            print(chassis + ' is not supported for updates.')
            sys.exit(1)
        
        print('We are dealing with a ' + chassis + ', BIOS version ' + bios_version + ' and DRAC firmware ' + drac_version)
                
        drac_upgrade(chassis, drac_ip, drac_user, drac_pass, drac_upgrade_version)
        # Let DRAC settle for 10 minutes after upgrade (needs time to upgrade itself and restart)
        sleep(600)

if __name__ == "__main__":
    main()