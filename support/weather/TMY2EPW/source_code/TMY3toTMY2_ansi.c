/*************************************************************************\
 National Renewable Energy Laboratory
 Electric Systems Center

 Program: TMY3toTMY2_ansi.c
  Author: Steve Wilcox
    Date: 2008-03-18

 Description:  Converts TMY3 files to TMY2

   Usage: 
   
   Compile:	  gcc -o Tmy3toTMY2_ansi TMY3toTMY2_ansi.c
   
\**************************************************************************
					Modifications
					*************
	Converted to ANSI C by Mary Anderberg 2008-05-22.
	
**************************************************************************/


#include <string.h>
#include <stdio.h>
#include <math.h>
#include <stdlib.h>

#define TMY3_FORMAT "%d/%d/%d,%d:%*d,%f,%f,%f,%d,%d,%f,%d,%d,%f,%d,%d,%f,%d,%d,%f,%d,%d,%f,%d,%d,%f,%d,%d,%f,%c,%d,%f,%c,%d,%f,%c,%d,%f,%c,%d,%f,%c,%d,%f,%c,%d,%f,%c,%d,%f,%c,%d,%f,%c,%d,%f,%c,%d,%f,%c,%d,%f,%c,%d,%*f,%*c,%*d,%*f,%*f,%*c,%*d"

#define TMY2_FORMAT " %02d%02d%02d%02d%04d%04d%04d%c%1d%04d%c%1d%04d%c%1d%04d%c%1d%04d%c%1d%04d%c%1d%04d%c%1d%02d%c%1d%02d%c%1d%04d%c%1d%04d%c%1d%03d%c%1d%04d%c%1d%03d%c%1d%03d%c%1d%04d%c%1d%05d%c%1d%1d%1d%1d%1d%1d%1d%1d%1d%1d%1d%03d%c%1d%03d%c%1d%03d%c%1d%02d%c%1d\n"
#define DEG2RAD 0.0174532925
#define VERSION "Version 1.0  (2008-03-18)"
#define MAX_PATHNAME_LEN 260


void process_file(char *in_fname, char *out_fname);
int rad_unc(int unc);
int met_unc(int flg);
char met_source(int flg);
char rad_source(int radflg, char metflg );
void quit_pgm(void);
void get_in_file(void);
void get_out_file(void);


int main (int argc, char *argv[])
{
	char	in_fname[MAX_PATHNAME_LEN],
			out_fname[MAX_PATHNAME_LEN],
			ok;
			
	if (argc < 2)
	{
		fprintf(stderr, 
			"\n                       DATA USE DISCLAIMER AGREEMENT\n"
			"                                 (\"Agreement\")\n\n"

			"This data and software (\"Data\") is provided by the National Renewable Energy\n"
			"Laboratory (\"NREL\"), which is operated by the Midwest Research Institute\n"
			"(\"MRI\") for the U.S. Department Of Energy (\"DOE\").\n\n"

			"Access to and use of these Data shall impose the following obligations on the\n"
			"user, as set forth in this Agreement.  The user is granted the right, without\n"
			"any fee or cost, to use, copy, modify, alter, enhance and distribute these\n"
			"Data for any purpose whatsoever, provided that this entire notice appears in\n"
			"all copies of the Data.  Further, the user agrees to credit DOE/NREL/MRI in\n"
			"any publication that results from the use of these Data.  The names\n"
			"DOE/NREL/MRI, however, may not be used in any advertising or publicity to\n"
			"endorse or promote any products or commercial entities unless specific\n"
			"written permission is obtained from DOE/NREL/MRI.  The user also understands\n"
			"that DOE/NREL/MRI is not obligated to provide the user with any support,\n"
			"consulting, training or assistance of any kind with regard to the use of\n"
			"these Data or to provide the user with any updates, revisions or new versions\n"
			"of these Data.\n\n"
			"Press <RETURN> to continue. . .");

		ok = getchar();

		fprintf(stderr, 
			"\rYOU AGREE TO INDEMNIFY DOE/NREL/MRI, AND ITS SUBSIDIARIES, AFFILIATES,\n"
			"OFFICERS, AGENTS, AND EMPLOYEES AGAINST ANY CLAIM OR DEMAND, INCLUDING\n"
			"REASONABLE ATTORNEYS' FEES, RELATED TO YOUR USE OF THESE DATA.  THESE DATA\n"
			"ARE PROVIDED BY DOE/NREL/MRI \"AS IS\" AND ANY EXPRESS OR IMPLIED WARRANTIES,\n"
			"INCLUDING BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND\n"
			"FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL\n"
			"DOE/NREL/MRI BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR\n"
			"ANY DAMAGES WHATSOEVER, INCLUDING BUT NOT LIMITED TO CLAIMS ASSOCIATED WITH\n"
			"THE LOSS OF DATA OR PROFITS, WHICH MAY RESULT FROM AN ACTION IN CONTRACT,\n"
			"NEGLIGENCE OR OTHER TORTIOUS CLAIM THAT ARISES OUT OF OR IN CONNECTION WITH\n"
			"THE ACCESS, USE OR PERFORMANCE OF THESE DATA.\n\n");

				fprintf(stderr, "usage: TMY3toTMY2_ansi <input file name>\n"
						"       Converts TMY3 format to TMY2 format\n"
						"       Output goes to the standard console output.\n"
						"       %s\n", VERSION);
		


		exit(1);
	}

	
	strcpy(in_fname, argv[1]);
	strcpy(out_fname, "");
	
	process_file(in_fname, out_fname);
	return 0;
}


void process_file(char *in_fname, char *out_fname)
{

	int		yr, mo, dy, hr,
			gloflg, dirflg, difflg, gloiflg, diriflg, dififlg, zeniflg, 
			glounc, dirunc, difunc, gloiunc, diriunc, difiunc, zeniunc,
			totunc, opqunc, drybunc, dewpunc, rhumunc, barounc,wspdunc, 
			wdirunc, horvunc, chgtunc, pwatunc, aodunc;
	
	char	site_id[20],
		    site_name[100],
		    site_state[3],
		    ns[2], ew[2],
			io[2000], totflg, opqflg, drybflg, dewpflg, rhumflg, baroflg, 
			wspdflg, wdirflg, horvflg, chgtflg, pwatflg, aodflg;
			
	float	etr, etrn, glo, dir, dif, tot, opq, dryb, dewp, rhum, baro, wspd, 
			wdir, horv, chgt, pwat, aod, gloi, diri, difi, zeni,
			lat, lon, elev, tzone;
	
	
	FILE *infile, *outfile;
	
	if (!*out_fname)
		outfile = stdout;
	else
	{
		if ((outfile = fopen(out_fname, "wt")) == NULL)
		{
			sprintf(io, "Cannot open output file <%s>.\n -- Processing halted.", out_fname);
		}
	}
	
	if ((infile = fopen(in_fname, "rt")) == NULL)
	{
		sprintf(io, "Cannot open input file <%s>\n -- Processing halted.", in_fname);

	}
	else
	{


		fgets (io, 1999, infile); // Station header
		
		/* scan the header */
		sscanf(io, "%6s,\"%[^\"]\",%2s,%f,%f,%f,%f", site_id, site_name, site_state, &tzone, &lat, &lon, &elev);

		*(site_name+22) = '\0'; // limit name to 22 characters

		strcpy(ns, lat < 0 ? "S" : "N");
		strcpy(ew, lon < 0 ? "W" : "E");

		fprintf(outfile, "%6s %-22s %2s%4.0f %1s %02d%3d %1s %3d%3d%6.0f\n",
			site_id, site_name, site_state, tzone, 
			ns, (int)fabs(lat), (int)((fabs(lat) - (int)fabs(lat)) * 60 + 0.5),
			ew, (int)fabs(lon), (int)((fabs(lon) - (int)fabs(lon)) * 60 + 0.5),
			elev);

		fgets (io, 1999, infile); // purge column header
		fgets (io, 1999, infile); // priming read

		while (!feof(infile))
		{
			/* read the input line */
			sscanf(io, TMY3_FORMAT,
				&mo, &dy, &yr, &hr, &etr, &etrn,
				&glo, &gloflg, &glounc, &dir, &dirflg, &dirunc, &dif, &difflg, &difunc, 
				&gloi, &gloiunc, &gloiflg, &diri, &diriunc, &diriflg, &difi, &difiunc, &dififlg, &zeni, &zeniunc, &zeniflg,
				&tot, &totflg, &totunc, &opq, &opqflg, &opqunc, 
				&dryb, &drybflg, &drybunc, &dewp, &dewpflg, &dewpunc, &rhum, &rhumflg, &rhumunc, &baro, &baroflg, &barounc, 
				&wdir, &wdirflg, &wdirunc, &wspd, &wspdflg, &wspdunc, &horv, &horvflg, &horvunc, &chgt, &chgtflg, &chgtunc, &pwat, &pwatflg, &pwatunc, &aod, &aodflg, &aodunc);
			
			/* covert to TMY2 units and bound field size for missing values */
			if (dryb > -9000.0)
				dryb *= 10.0;
			else
				dryb = -990.0;
				
			if (dewp > -9000.0)
				dewp *= 10.0;
			else
				dewp = -990.0;
			
			if (rhum < -9000.0)
				rhum = -99.0;
			
			if (tot < -900.0)
				tot = 99;
				
			if (opq < -900.0)
				opq = 99;
				
			if (baro < -9000.0)
				baro = -990.0;
				
			if (wspd > -9000.0)
				wspd *= 10.0;
			else
				wspd = -99.0;
				
			if (wdir < -9000.0)
				wdir = -99;
				
			if (horv > -9000.0)
				horv /= 100.0;
			else
				horv = 9999.0;
			
			if (chgt < -9000.0)
				chgt = 99999.0;
				
			if (pwat > -9000.0)
				pwat *= 10.0;
			else
				pwat = -99.0;
				
			if (aod > -9000.0)
				aod *= 1000.0;
			else
				aod = -99.0;
				
			if (glo < -9000.0)
				glo = -990.0;
				
			if (dir < -9000.0)
				dir = -990.0;
				
			if (dif < -9000.0)
				dif = -990.0;
			
			if (gloi > -9000.0)
				gloi /= 100.0;

			if (diri > -9000.0)
				diri /= 100.0;

			if (difi > -9000.0)
				difi /= 100.0;

			if (zeni > -9000.0)
				zeni /= 10.0;

			/* output with flags and move on to next record */
			fprintf(outfile, TMY2_FORMAT,
				yr%100, mo, dy, hr, (int)etr, (int)etrn, 
				(int)glo, rad_source(gloflg, totflg > opqflg ? totflg : opqflg), rad_unc(glounc), 
				(int)dir, rad_source(dirflg, totflg > opqflg ? totflg : opqflg), rad_unc(dirunc), 
				(int)dif, rad_source(difflg, totflg > opqflg ? totflg : opqflg), rad_unc(difunc), 
				(int)gloi,'I', rad_unc(glounc), 
				(int)diri,'I', rad_unc(dirunc),
				(int)difi,'I', rad_unc(difunc),
				(int)zeni,'I', rad_unc(glounc), 
				(int)tot, totflg, totunc, (int)opq, opqflg, opqunc,
				(int)(dryb), drybflg, drybunc, (int)dewp, dewpflg, dewpunc, 
				(int)rhum, rhumflg, rhumunc, (int)baro, baroflg, barounc,
				(int)wdir, wdirflg, wdirunc, (int)wspd, wspdflg, wspdunc,
				(int)(horv), horvflg, horvunc, (int)chgt, chgtflg, chgtunc,
				9,9,9,9,9,9,9,9,9,9,
				(int)pwat, pwatflg, pwatunc, 
				(int)aod, aodflg, aodunc, 
				999, '?', 0,
				99, '?', 0);
			
			fgets(io, 1999, infile);
		}
	}
	fclose(infile);
	fclose(outfile);
}







/**************************************************************************\

  Function rad_unc()
  
  Maps percent uncertainty to TMY2 uncertainty categories
						 
\**************************************************************************/
int rad_unc(int unc)
{
	int uflg;
	
	if (unc < 2.0)
		uflg = 1;
	else if (unc < 4.0)
		uflg = 2;
	else if (unc < 6.0)
		uflg = 3;
	else if (unc < 9.0)
		uflg = 4;
	else if (unc < 13.0)
		uflg = 5;
	else if (unc < 18.0)
		uflg = 6;
	else if (unc < 25.0)
		uflg = 7;
	else if (unc < 35.0)
		uflg = 8;
	else if (unc < 50.0)
		uflg = 9;
	else
		uflg = 0;
		
	return uflg;
}

int met_unc(int flg)
{
	
	return (flg < 10 ? 7 : 8);
}
					

/**************************************************************************\

  Function met_source()
  
  Maps meteorological flags to TMY2 met source flags
						 
\**************************************************************************/
char met_source(int flg)
{
	char source;
	
	if (flg == 99)
		source = '?';
	else if (flg < 10)
		source = 'A';
	else if (flg == 51)
		source = 'B';
	else if (flg == 52)
		source = 'C';
	else if (flg < 99)
		source = 'E';
	else
		source = '?';
	
	return source;
}

/**************************************************************************\

  Function rad_source()
  
  Maps radiation and meteorological flags to TMY2 source flags
						 
\**************************************************************************/
char rad_source(int radflg, char metflg )
{
	char source;
	
	if (radflg == 2 || radflg == 3)	// satellite
		source = 'K';
	else if (metflg == '?')
		source = '?';
	else if (metflg == 'A' || metflg == 'B')	// METSTAT observed cloud
		source = 'E';
	else 
		source = 'F';						// METSTAT interpolated
	
	return source;
}

