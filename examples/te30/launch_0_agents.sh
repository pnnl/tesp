(export FNCS_FATAL=NO && exec gridlabd -D USE_FNCS TE_Challenge0.glm &> gridlabd.log &)
(export FNCS_FATAL=NO && exec python double_auction.py input/auction_registration.json TE_Challenge0 &> auction.log &)
# (export FNCS_FATAL=NO && exec python house_controller.py input/controller_registration_F1_house_B0_thermostat_controller.json &)