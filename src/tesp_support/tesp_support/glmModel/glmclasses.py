from model import GLModel
from modifier import GLMModifier
from tesp_support.data import feeders_path

if __name__ == '__main__':
    modelfile = GLModel()
    modobject = GLMModifier()
    tval = modelfile.read_glm(feeders_path + "R1-12.47-1.glm")
    # tval = modobject.read_model(feeders_path + "R1-12.47-1.glm")
