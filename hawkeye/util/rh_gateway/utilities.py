"""
Copyright: 2014 Geon Technologies, LLC

This file is part of HAWKEYE.

HAWKEYE is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Thomas Goodwin
@summary: Simple set of utilities for searching and splitting splitting dictionaries
"""

# Compares dictlista to dictlistb using the provided keys.
# The dictionaries in each list must all support the provided keys.
# @return indices Indexes where a dictionary in dictlista was not 
#                 found in dictlistb.
def indicesUniqueOnKeys(dictlista, dictlistb, keys):
    indices = []
    for dax, da in enumerate(dictlista):
        found = False
        for db in dictlistb:
            match = True
            for key in keys:
                if da[key] != db[key]:
                    match = False;
                    break
            if match:
                found = True
        if not found:
            indices.append(dax)
    return indices

# Takes 2 lists of dictionaries and splits them into added and removed
# lists using the provided keys.  All keys must be supported by the 
# dictionaries in each list.
# @return added, removed  What they say on the tin.
def splitDictLists(newList, oldList, keys):
    addIdxs = indicesUniqueOnKeys(newList, oldList, keys)
    removeIdxs = indicesUniqueOnKeys(oldList, newList, keys)
    return ([newList[i] for i in addIdxs], 
            [oldList[i] for i in removeIdxs])
