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

# Global variable to hold the full Building Block tree for cross referencing.
# Might want to refactor, but perhaps the structure of RES xml won't allow for that.
bbtree = ''


def bbprocess(bb):
    """Open Building Block file, parse as xml and dispatch thes sections to their respective parser functions"""
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
                for element in moduleroot.getchildren():
                    create_module_page(element)

            # Finally we create an index page to tie it all together
            index = {
                'filename': bb,
                'modules': []
            }
            for module_element in bbtree.findall('/buildingblock/modules/module'):
                module_name = module_element.find('.//properties/name').text
                module_guid = module_element.find('.//properties/guid').text
                module = {
                    'name': module_name,
                    'guid': module_guid
                }
                index['modules'].append(module)

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


def task_to_dict(t):
    """Returns a dictionary from a task xml element"""
    # Determine type and gather common info
    tasktype = t.find('.//properties/type').text
    taskdict = {
        'type': tasktype,
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

    # Finally we return the dictionary to the caller.
    return taskdict


def create_module_page(e):
    """Creates a html from jinja template and a module element"""
    folderpath = '/'.join([f.text for f in e.findall('.//folder/name')])
    paramroot = e.find('.//tasks/task/parameters')
    # we need to grab the non hidden tasks, thanks RES
    actual_tasks = e.xpath('.//tasks/task[not(@hidden)]')
    module = {
        'title': (e.find('.//name')).text,
        'guid': (e.find('.//guid')).text,
        'enabled': (e.find('.//enabled')).text,
        'description': (e.find('.//description')).text,
        'version': (e.find('.//version')).text,
        'versioncomment': (e.find('.//versioncomment')).text,
        'folderpath': folderpath,
        'parameters': [],
        'tasks': []
    }
    if len(paramroot) > 0:
        for element in paramroot.getchildren():
            module['parameters'].append(parameter_to_dict(element))
    for task in actual_tasks:
        module['tasks'].append(task_to_dict(task))
    # print(module['title'], module['guid'])
    template = env.get_template('module.html')
    html = template.render(module=module)
    filename = output_folder + "/modules/" + module['guid'] + ".html"
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
    # ToDo Add argument handler for input file
    # For now we grab cwd/Export.xml or busto
    buildingblock = args.file
    bbprocess(buildingblock)

if __name__ == "__main__":
    # execute only if run as a script
    main()
