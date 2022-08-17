# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from model import GLModel
from modifier import GLMModifier
import model
def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.




# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')
    modelfile = GLModel()
    modobject = GLMModifier()
    tval = modelfile.read_glm("testing.glm")
    #tval = modobject.read_model("testing.glm")




# See PyCharm help at https://www.jetbrains.com/help/pycharm/
