// Copyright (C) 2021-2023 Battelle Memorial Institute
// file: helicsshed.py


import fncs.JNIfncs;

public class loadshed {
    public static void main(String[] args) {
        long time_granted=0;
        long time_stop=Long.parseLong(args[0]);
        JNIfncs.initialize();
        assert JNIfncs.is_initialized();

        while (time_granted < time_stop) {
            time_granted = JNIfncs.time_request(time_stop);
            String[] events = JNIfncs.get_events();
            for (int i=0; i<events.length; ++i) {
                String value = JNIfncs.get_value(events[i]);
                String[] values = JNIfncs.get_values(events[i]);
                assert value == values[0];
                if (events[i].equals("sw_status")) {
                    JNIfncs.publish("sw_status", values[0]);
                    System.out.printf("** publishing sw_status=%s\n", values[0]);
                }
                for (int j=0; j<values.length; ++j) {
                    System.out.printf("\t%d\t[%d] %s\t[%d] %s\n", time_granted, i, events[i], j, values[j]);
                }
            }
        }
        JNIfncs.end();
        assert !JNIfncs.is_initialized();
    }
}

