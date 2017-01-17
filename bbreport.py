#!/usr/bin/env python
"""BBReport aims to produce more useful reports based on RESAM Building Blocks (XML)."""

# import builtins
import argparse
import shutil
import os

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
            bbtree = (etree.parse(buildingblock))
            moduleroot = bbtree.find("/buildingblock/modules")
            if len(moduleroot) > 0:
                os.makedirs(output_folder + '/modules')
                for element in moduleroot.getchildren():
                    create_module_page(element)

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


def main():
    """Main function, checks for arguments and default files."""
    parser = argparse.ArgumentParser()
    parser.parse_args()
    # ToDo Add argument handler for input file
    # For now we grab cwd/Export.xml or busto
    buildingblock = './Export.xml'
    bbprocess(buildingblock)

if __name__ == "__main__":
    # execute only if run as a script
    main()
