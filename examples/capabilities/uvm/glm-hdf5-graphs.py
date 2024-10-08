import networkx as nx
import numpy as np
import h5py as h5
import matplotlib.pyplot as plt

"""This class is used to read an evdet h.5 file and generate a chart for the total
average values for SOC and charging power across all evs

"""


class GraphGLMH5:
    def __init__(self):
        self.h5_filename = ""
        self.h5_data = None
        self.h5_data_set = None
        self.h5_hours = list()
        self.h5_unique_times = list()
        self.h5_unique_hours = list()
        self.h5_soc_avg = list()
        self.h5_total_soc_values = list()
        self.h5_charge_avg = list()
        self.h5_total_charge_values = list()
        self.h5_soc_max = 0
        self.h5_charge_max = 0

    """read_h5s_file reads an evdet file and loads the GraphGLMH5 object

    Args:
        file_path (str): the fill path the evdet file that is to be read
        
    Returns:
        (boolean): True if successful and False if unable to read the file
    """
    def read_h5_file(self, file_path):
        try:
            self.h5_data = h5.File(file_path, 'r')
            return True
        except:
            return False

    """get_ev_dataset pulls the index1 data from the h5 data object

    Args:
        None

    Returns:
        (boolean): True if successful and False if unable to read the file
    """
    def get_ev_dataset(self, index_name):
        try:
            # print(list(self.h5_data.keys()))
            self.h5_data_set = self.h5_data[index_name]
            # print(type(self.h5_data_set))
            # print(list(self.h5_data["Metadata"]))
            return True
        except:
            return False

    """get_total_avg_data reads an h5 evdet file and then processes the data and loads the
    averaging data for SOC and charging power into the GraphGLMH5 object

    Args:
        file_path (str): the fill path the evdet file that is to be read

    Returns:
        None
    """
    def get_total_avg_data(self, file_path):
        self.read_h5_file(file_path)
        key_list = list(self.h5_data.keys())
        tlist = list()
        indexed_time = 0
        total_soc = 0
        total_charge = 0
        for i in range(1,len(key_list)):
            print(key_list[i])
            tlist = list()
            self.get_ev_dataset(key_list[i])
            for j in range(len(self.h5_data_set)):
                data_array= self.h5_data_set[j]
                if j == 0:
                    indexed_time =data_array[0]
                    total_soc = 0
                    total_charge = 0
                if indexed_time != data_array[0]:
                    indexed_time = data_array[0]
                    self.h5_unique_times.append(indexed_time)
                    self.h5_soc_avg.append(total_soc)
                    self.h5_charge_avg.append(total_charge)
                    self.h5_unique_hours.append(indexed_time / 3600)
                    total_soc = 0
                    total_charge = 0
                else:
                    total_soc += data_array[3]
                    total_charge += data_array[6]
            print(self.h5_unique_hours)
            print(self.h5_soc_avg)
            print(self.h5_charge_avg)


    """plot_charge_totals generates matplotlib graph for total average charging power across all evs
    using the data found in the GraphGLMH5 object
    

    Args:
        None

    Returns:
        None
    """
    def plot_charge_totals(self):
        fig, axs = plt.subplots()
        plt.plot(self.h5_unique_hours, self.h5_charge_avg)
        plt.title("Total EV charging power across all EVs")
        axs.set_xlabel('Time (hrs)')
        axs.set_ylabel("Total Charging Power")
        plt.show()

    """plot_soc_totals generates matplotlib graph for total SOC across all evs
    using the data found in the GraphGLMH5 object


    Args:
        None

    Returns:
        None
    """

    def plot_soc_totals(self):
        fig, axs = plt.subplots()
        plt.plot(self.h5_unique_hours, self.h5_soc_avg)
        plt.title("Average of the SOC across all EVs")
        axs.set_xlabel('Time (hrs)')
        axs.set_ylabel('Average SOC')
        plt.show()

def _test1():
    testPlotData = GraphGLMH5()
    testPlotData.get_total_avg_data("/home/d3k205/grid/tesp/examples/capabilities/uvm/out_evchargerdet.h5")
    testPlotData.plot_charge_totals()
    testPlotData.plot_soc_totals()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    _test1()

