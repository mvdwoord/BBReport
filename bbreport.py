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
    autoescape=select_autoescape(['html', 'xml'])
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


def bbprocess(bb):
    """Open Building Block file, parse as xml and dispatch thes sections to their respective parser functions"""
    try:
        with open(bb) as buildingblock:
            print("Processing {}".format(bb))
            # clear output directory
            shutil.rmtree(output_folder)
            os.makedirs(output_folder)
            bbtree = (etree.parse(buildingblock))
            moduleroot = bbtree.find("/buildingblock/modules")
            print(moduleroot, len(moduleroot))
            for element in moduleroot.getchildren():
                create_module_page(element)

    except IOError as err:
        print("Error opening {}\n{}".format(bb, err))


def create_module_page(e):
    """Creates a html from jinja template and a module element"""
    # print("creating html for element {}".format(e.tag))
    module = {
        'title': (e.find('.//name')).text,
        'guid': (e.find('.//guid')).text
    }
    # print(module['title'], module['guid'])
    template = env.get_template('module.html')
    html = template.render(module=module)
    filename = output_folder + "/module_" + module['guid'] + ".html"
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
