#!/usr/bin/env python
"""BBReport aims to produce more useful reports based on RESAM Building Blocks (XML)."""

# import builtins
import argparse
import binascii
import os
import shutil
import zlib

# import 3rd party
from lxml import etree
from jinja2 import Environment, PackageLoader, select_autoescape
env = Environment(
    loader=PackageLoader('bbreport', 'templates'),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    extensions=['jinja2_highlight.HighlightExtension']
)

# GPL
"""
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Authorship information
__author__ = "Maarten van der Woord"
__copyright__ = "Copyright 2017, Maarten van der Woord"
__credits__ = ["Maarten van der Woord"]
__license__ = "GNU GENERAL PUBLIC LICENSE Version 3"
__version__ = "0.1"
__maintainer__ = "Maarten van der Woord"
__email__ = "maarten@vanderwoord.nl"
__status__ = "Development"

# ToDo parameterize output folder
output_folder = "./output"

# Some lookup dicts for RES magic numbers
parameter_type = {
    '0': 'Text'
}

task_displayname = {
    'PWRSHELL': "Execute Powershell Command",
    'COMMAND': "Execute a Command",
    'DOWNLOAD': "Download a resource",
    'SHUTDOWN': "Shutdown or Reboot",
    'REGISTRY': "Apply Registry Settings",
    'FILEOPERATIONS': "PErform File Operations"
}

security_objecttype = {
    '1': "Set NTFS File/Folder Permissions",
    '2': "Set Registry Permissions",
    '3': "Set Share Permissions",
    '4': "Set Printer Permissions"
}

permission_action = {
    '1': "Allow",
    '2': "Deny",
    '3': "Delete"
}

""" Access masks are a special beast.
Full details: https://blogs.msdn.microsoft.com/openspecification/2010/04/01/about-the-access_mask-structure/
but we will stick to the values used in AM"""
access_mask = {
    # -1 is used for deletions, mask is irrelevant in such cases
    '-1': "",
    # NTFS / Fileshare permissions
    '1048854': "Write",
    '1179785': "Read",
    '1179817': "Read & Execute",
    '1180063': "Read & Write",
    '1180095': "Read, Write & Execute",
    '1245631': "Modify",
    '2032127': "Full Control",
    # Registry permissions
    '268435456': "Full Control",
    '-2147483648': "Read",
    # Printer permissions
    '131080': "Print",
    '983052': "Manage Printers",
    '983088': "Manage Documents",
    '983096': "Print & Manage Documents",
    '983100': "Manage Printers & Documents"
}

# Global variable to hold the full Building Block tree for cross referencing.
# Might want to refactor, but perhaps the structure of RES xml won't allow for that.
bbtree = ''


def process_buildingblock(bb):
    """Open Building Block file, parse as xml and dispatch the sections to their respective parser functions"""
    try:
        with open(bb) as buildingblock:
            print("Processing {}".format(bb))
            # clear output directory
            shutil.rmtree(output_folder)
            os.makedirs(output_folder)
            shutil.copyfile('./templates/bbreport.css', './output/bbreport.css')
            shutil.copyfile('./templates/vs.css', './output/vs.css')
            global bbtree
            bbtree = (etree.parse(buildingblock))

            # First item of business is creating all module pages
            moduleroot = bbtree.find("/buildingblock/modules")
            if len(moduleroot) > 0:
                os.makedirs(output_folder + '/modules')
                for module in moduleroot.getchildren():
                    create_module_page(module)

            # Next up is creating all module pages
            projectroot = bbtree.find("/buildingblock/projects")
            if len(projectroot) > 0:
                os.makedirs(output_folder + '/projects')
                for project in projectroot.getchildren():
                    create_project_page(project)

            # Finally we create an index page to tie it all together
            index = {
                'filename': bb,
                'projects': [],
                'modules': []
            }
            for project_element in bbtree.findall('/buildingblock/projects/project'):
                project = {
                    'name': project_element.find('.//properties/name').text,
                    'guid': project_element.find('.//properties/guid').text
                }
                index['projects'].append(project)

            for module_element in bbtree.findall('/buildingblock/modules/module'):
                module = {
                    'name': module_element.find('.//properties/name').text,
                    'guid': module_element.find('.//properties/guid').text
                }
                index['modules'].append(module)

            # Sort them alphabetically
            index['projects'] = sorted(index['projects'], key=lambda k: k['name'])
            index['modules'] = sorted(index['modules'], key=lambda k: k['name'])

            template = env.get_template('index.html')
            html = template.render(index=index)
            filename = output_folder + '/index.html'
            with open(filename, 'wt', encoding='utf-8') as file:
                file.write(html)

    except IOError as err:
        print("Error opening {}\n{}".format(bb, err))


def parameter_to_dict(p):
    """Retruns a dictionary from a param xml element"""
    value_element = p.find('.//value1')
    value = ""
    if value_element is not None:
        value = value_element.text
    parameterdict = {
        'name': (p.find('.//name')).text,
        'type': parameter_type.get(p.find('.//type').text, "Unknown"),
        'value': value,
        'description': (p.find('.//description')).text
    }
    return parameterdict


def projectmodule_to_dict(p):
    """Returns a dictionary from a module xml as linked from a project"""
    guid = p.find('.//guid').text
    xpath = '//modules/module/properties[guid/text()="' + guid + '"]'
    module_element = bbtree.xpath(xpath)[0]
    name = module_element.find('.//name').text
    enabled = p.find('.//enabled').text
    projectmoduledict = {
        'guid': guid,
        'name': name,
        'enabled': enabled
    }
    return projectmoduledict


def task_to_dict(t):
    """Returns a dictionary from a task xml element"""
    # Determine type and gather common info
    tasktype = t.find('.//properties/type').text
    displayname = task_displayname.get(tasktype, "Unknown (" + tasktype + ")")
    taskdict = {
        'type': tasktype,
        'displayname': displayname,
        'guid': t.find('.//properties/guid').text,
        'enabled': t.find('.//properties/enabled').text
    }
    # Tasks have type specific properties which need to be dealt with individually
    # We'll use the 'settings' of the taskdict to store a rendered partial table
    # based of the type's template. To be included in the main module template.
    if tasktype == "PWRSHELL":
        # usescript indicates if the script tab is used. If not, the source code
        # needs to come from a resource. Value is always yes or no.
        usescript = t.find('.//settings/usescript').text
        if usescript == 'yes':
            pwrshell = {
                'source': "Script Tab",
                'code': t.find('.//settings/source').text
            }
        else:
            pwrshell = {
                'source': "Resource File",
                'resourcename': t.find('.//settings/resourcename').text,
                'resourceguid': t.find('.//settings/resourceguid').text,
                # ToDo grab and base64 decode source from XBB
                'code': 'To Be Decoded somehow...'
            }
        taskdict['settings'] = env.get_template('PWRSHELL.html').render(pwrshell=pwrshell)

    elif tasktype == "SHUTDOWN":
        message = t.find('.//settings/message').text
        reboot = t.find('.//settings/reboot').text
        force = t.find('.//settings/force').text
        check4users = t.find('.//settings/check4users').text
        timeout = t.find('.//settings/timeout').text
        shutdown = {
            'message': message,
            'reboot': reboot,
            'force': force,
            'check4users': check4users,
            'timeout': timeout
        }
        if message == 'yes':
            messagetext = t.find('.//settings/messagetext').text
            duration = t.find('.//settings/duration').text
            shutdown['messagetext'] = messagetext
            shutdown['duration'] = duration
        if reboot == 'yes':
            waitforreboot = t.find('.//settings/waitforreboot').text
            shutdown['waitforreboot'] = waitforreboot

        taskdict['settings'] = env.get_template('SHUTDOWN.html').render(shutdown=shutdown)

    elif tasktype == "DOWNLOAD":
        ysnlog = t.find('.//settings/ysnlog').text
        ysndestination = t.find('.//settings/ysndestination').text
        download = {
            'ysnlog': ysnlog,
            'ysndestination': ysndestination,
            'resources': []
        }
        if ysndestination == 'yes':
            destination = t.find('.//settings/destination').text
            download['destination'] = destination
        resources_string = t.find('.//settings/resources').text
        for resourceguid in resources_string.split(','):
            xpath = '//resource[properties/guid="' + resourceguid + '"]'
            resource_element = bbtree.xpath(xpath)[0]
            guid = resource_element.find('.//properties/guid').text
            version = resource_element.find('.//properties/version').text
            versioncomment = resource_element.find('.//properties/versioncomment').text
            resourcetype = resource_element.find('.//properties/type').text
            resource = {
                'guid': guid,
                'version': version,
                'versioncomment': versioncomment,
                'type': resourcetype
            }
            # Here we add the resource type specific attributes
            if resourcetype == 'DATABASE':
                resource['file'] = resource_element.find('.//properties/file').text
                resource['parsefilecontent'] = resource_element.find('.//properties/parsefilecontent').text
                resource['skipenvironmentvariables'] = resource_element.find('.//properties/skipenvironmentvariables').text
                resource['comment'] = resource_element.find('.//properties/comment').text
                resource['enabled'] = resource_element.find('.//properties/enabled').text
                resource['crc32'] = resource_element.find('.//properties/crc32').text
                resource['folderpath'] = '/'.join([f.text for f in resource_element.findall('.//folder/name')])
            elif resourcetype == 'FILESHARE':
                resource['file'] = resource_element.find('.//properties/file').text
            elif resourcetype == 'AMRESOURCEPACKAGE':
                resource['name'] = resource_element.find('.//properties/name').text
            elif resourcetype == 'URLRESOURCE':
                resource['file'] = resource_element.find('.//properties/file').text

            download['resources'].append(resource)

        taskdict['settings'] = env.get_template('DOWNLOAD.html').render(download=download)

    elif tasktype == 'FILEOPERATIONS':
        fileoperationtasks = []
        for task_element in t.findall('.//fileoperationtask'):
            fileoperationtask = {
                'type': task_element.find('.//type').text,
                'sourcelocation': task_element.find('.//sourcelocation').text,
                'hasdestination': False
            }
            if fileoperationtask['type'] in ['copy', 'move', 'rename']:
                fileoperationtask['hasdestination'] = True
                fileoperationtask['destinationlocation'] = task_element.find('.//destinationlocation').text
            # ToDo add support for ini file manipulation
            fileoperationtasks.append(fileoperationtask)

        taskdict['settings'] = env.get_template('FILEOPERATIONS.html').render(fileoperationtasks=fileoperationtasks)

    elif tasktype == 'REGISTRY':
        registryfile = unreszlib(t.find('.//regfile').text)

        taskdict['settings'] = env.get_template('REGISTRY.html').render(registryfile=registryfile)

    elif tasktype == 'SECURITY':

        permission = {
            'objecttype': security_objecttype[t.find('.//objecttype').text],
            'filename': t.find('.//filename').text,
            'replaceacl': t.find('.//replaceacl').text,
            'propagate': t.find('.//propagate').text,
            'permissions': []
        }
        # Special case for nicer display of task type
        taskdict['displayname'] = permission['objecttype']
        for permission_element in t.findall('.//permissions/permission'):
            permission_item = {
                'action': permission_action[permission_element.find('.//action').text],
                'account': permission_element.find('.//account').text,
                'right': access_mask[permission_element.find('.//permission').text]
            }
            permission['permissions'].append(permission_item)

        taskdict['settings'] = env.get_template('SECURITY.html').render(permission=permission)

    # Finally we return the dictionary to the caller.
    return taskdict


def create_module_page(m):
    """Creates a html from jinja template and a module element"""
    folderpath = '/'.join([f.text for f in m.findall('.//folder/name')])
    paramroot = m.find('.//tasks/task/parameters')
    # we need to grab the non hidden tasks, thanks RES
    actual_tasks = m.xpath('.//tasks/task[not(@hidden)]')
    module = {
        'title': (m.find('.//name')).text,
        'guid': (m.find('.//guid')).text,
        'enabled': (m.find('.//enabled')).text,
        'description': (m.find('.//description')).text,
        'version': (m.find('.//version')).text,
        'versioncomment': (m.find('.//versioncomment')).text,
        'folderpath': folderpath,
        'parameters': [],
        'tasks': []
    }
    if len(paramroot) > 0:
        for element in paramroot.getchildren():
            module['parameters'].append(parameter_to_dict(element))
    for task in actual_tasks:
        module['tasks'].append(task_to_dict(task))

    template = env.get_template('module.html')
    html = template.render(module=module)
    filename = output_folder + "/modules/" + module['guid'] + ".html"
    with open(filename, 'wt', encoding='utf-8') as file:
        file.write(html)


def create_project_page(p):
    folderpath = '/'.join([f.text for f in p.findall('.//folder/name')])
    paramroot = p.find('.//properties/parameters')
    moduleroot = p.find('.//modules')
    project = {
        'title': (p.find('.//name')).text,
        'guid': (p.find('.//guid')).text,
        'enabled': (p.find('.//enabled')).text,
        'description': (p.find('.//description')).text,
        'version': (p.find('.//version')).text,
        'versioncomment': (p.find('.//versioncomment')).text,
        'folderpath': folderpath,
        'parameters': [],
        'modules': []
    }

    if len(paramroot) > 0:
        for element in paramroot.getchildren():
            project['parameters'].append(parameter_to_dict(element))
    if len(moduleroot) > 0:
        for module in moduleroot.getchildren():
            project['modules'].append(projectmodule_to_dict(module))

    template = env.get_template('project.html')
    html = template.render(project=project)
    filename = output_folder + "/projects/" + project['guid'] + ".html"
    with open(filename, 'wt', encoding='utf-8') as file:
        file.write(html)


def unreszlib(reszlib):
    """Helper function to extract text from RESZLIB values"""
    return zlib.decompress(binascii.unhexlify(reszlib[22:])).decode("utf-8")


def main():
    """Main function, checks for arguments and default files."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file',
                        default='./Export.xml',
                        metavar='BuildingBlock',
                        help='The Building Block XML File to process')
    args = parser.parse_args()
    buildingblock = args.file
    process_buildingblock(buildingblock)

if __name__ == "__main__":
    # execute only if run as a script
    main()
