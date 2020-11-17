# Reduced Order Model Test Case

- *arl.py; the aggregate responsive load (ARL) agent 
- *rnn.py; recurrent neural networks (RNN) used in the ARL agent 
- *process_input_data.py; functions to initialize the ARL agent   
- *metrics_result.py; make plots of the simulation result.

## Requirement for running a test case 

1. Install Pytorch (1.3.0 or a later version) with CUDA (10.1 or a later version) https://pytorch.org/get-started/locally/
2. Check CUDA availability by torch.cuda.is_available()

## To run a case from the GUI monitor:  

1. change the number (between 1 to 1500) in launch_auction.py as the total house number
2. invoke "gui" (Windows)
3. from the GUI, click Open to open the file tesp_monitor.json from this directory
4. from the GUI, click Start All to launch the simulations

## Simulation time  
For simulation time reduction, simulations with the ARL require a GPU for the neural networks computation. However, it can still run very slow without a GPU. Use torch.cuda.get_device_name(0) to check if the GPU of a graphic card is being used by Pytorch