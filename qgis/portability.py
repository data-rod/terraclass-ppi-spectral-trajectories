"""Store local QGIS layer references relative to the map directory."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import re
import xml.etree.ElementTree as ET

def make_portable(project):
    project=Path(project).resolve()
    with ZipFile(project) as z:members={name:z.read(name) for name in z.namelist()}
    name=next(n for n in members if n.endswith('.qgs'))
    root=ET.fromstring(members[name])
    changes=[]
    root.attrib.pop('saveUser',None)
    for element in root.iter():
        for key,value in list(element.attrib.items()):
            if key=='source' and re.match(r'^[A-Za-z]:[/\\]',value):
                file,separator,provider=value.partition('|')
                filename=file.replace('\\','/').rsplit('/',1)[-1]
                if not (project.parent/'data'/filename).is_file():
                    raise ValueError('A local project reference has no corresponding archived map file')
                relative='./data/'+filename+(separator+provider if separator else '')
                element.set(key,relative);changes.append((value,relative))
    members[name]=ET.tostring(root,encoding='UTF-8',xml_declaration=True)
    temporary=project.with_suffix('.pending')
    with ZipFile(temporary,'w',ZIP_DEFLATED) as z:
        for member,content in members.items():z.writestr(member,content)
    temporary.replace(project)
    return changes
