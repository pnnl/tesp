import psst.cli as p

#p.scuc("C:/Users/huan289/Qiuhua/FY2016_Project_Transactive_system/ERCOTTestSystem/AMES-V5.0/DataFiles/SCUCReferenceModel.dat", "C:/Users/huan289/Qiuhua/FY2016_Project_Transactive_system/ERCOTTestSystem/AMES-V5.0/DataFiles/GenCoSchedule.dat", "cbc")
#p.scuc("C:/Users/huan289/Qiuhua/FY2016_Project_Transactive_system/ERCOTTestSystem/AMES-V5.0/DATA/PSST_TestCases/PSL_3bus_largeE.dat", "C:/Users/huan289/Qiuhua/FY2016_Project_Transactive_system/ERCOTTestSystem/AMES-V5.0/psst/tests/GenCoSchedule.dat", "cbc")
p.scuc("/home/osboxes/grid/repository/ERCOTTestSystem/AMES-V5.0/DATA/PSST_TestCases/PSL_3bus_margin.dat", "/home/osboxes/grid/repository/ERCOTTestSystem/AMES-V5.0/psst/tests/GenCoSchedule.dat", "cplex")
