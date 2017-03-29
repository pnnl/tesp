/*	Copyright (C) 2017 Battelle Memorial Institute */


void read_load_profile(char *file_name, double load_profile[][288], int subst_num);

void read_model_dim(char *file_name, int *nbrows, int *nbcolumns, int *ngrows, int *ngcolumns,
              int *nbrrows, int *nbrcolumns, int *narows, int *nacolumns,
              int *ncrows, int *nccolumns, int *nFNCSBus, int *nFNCSSub, int *noffGen);

void read_model_data(char *file_name, int nbrows, int nbcolumns, int ngrows, int ngcolumns,
              int nbrrows, int nbrcolumns, int narows, int nacolumns,
              int ncrows, int nccolumns, int nFNCSbuses, int nFNCSsubst, int noffgelem,
              double *baseMVA, double *bus, double *gen,
              double *branch, double *area, double *costs, int *BusFNCS,
              char SubNameFNCS[][15], int *SubBusFNCS,
              int *offline_gen_bus, double *ampFacto);
