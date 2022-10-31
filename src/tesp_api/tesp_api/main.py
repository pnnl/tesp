# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: main.py

# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import json

from model import GLModel
from modifier import GLMModifier

from data import entities_path
from data import feeders_path


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    modelfile = GLModel()
    modobject = GLMModifier()
    tval = modelfile.read(feeders_path + "R1-12.47-1.glm")
    #tval = modobject.read_model(feeders_path + "R1-12.47-1.glm")

    # for name in modelfile.entities:
    #     modelfile.entities[name].table_print()

    # Output json with new parameters
    op = open(entities_path + 'glm_objects2.json', 'w', encoding='utf-8')
    json.dump(modelfile.entitiesToJson(), op, ensure_ascii=False, indent=2)
    op.close()

    modelfile.write(entities_path + "test.glm")
    modelfile.instancesToSQLite()
    print(modelfile.entitiesToHelp())
    print(modelfile.instancesToGLM())

    print(modelfile.entitiesToJson())
