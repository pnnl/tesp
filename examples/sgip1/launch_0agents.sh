(export FNCS_FATAL=NO && exec gridlabd SGIP1a.glm &> gridlabd.log &)
(export FNCS_FATAL=NO && exec python double_auction.py input/auction_registration.json SGIP1a &> auction.log &)
(export FNCS_FATAL=NO && exec python house_controller.py input/controller_registration_house1_R1_12_47_1_tm_507_thermostat_controller.json &)

