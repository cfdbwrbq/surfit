
/*------------------------------------------------------------------------------
 *	$Id$
 *
 *	Copyright (c) 2002-2006 by M. V. Dmitrievsky and V. N. Kutrunov
 *	See COPYING file for copying and redistribution conditions.
 *
 *	This program is free software; you can redistribute it and/or modify
 *	it under the terms of the GNU General Public License as published by
 *	the Free Software Foundation; version 2 of the License.
 *
 *	This program is distributed in the hope that it will be useful,
 *	but WITHOUT ANY WARRANTY; without even the implied warranty of
 *	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *	GNU General Public License for more details.
 *
 *	Contact info: surfit.sourceforge.net
 *----------------------------------------------------------------------------*/

#include "sstuff_ie.h"
#include <stdio.h>
#include <stdarg.h>

#ifdef HAVE_STRING_H
#include <string.h>
#endif

#include <time.h>
#include <errno.h>

#include "fileio.h"

#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif

#include <fcntl.h>

#if defined(_WIN32) || defined(__WIN32__) || defined(WIN32)
#include <io.h>
#endif

namespace surfit {

const char * error = "Error! ";
const char * warning = "Warning! ";
const char * debug = "Debug: ";

FILE * logfile = NULL;
char * logfilename = NULL;
int loglevel = LOG_MESSAGE;
int stop_on_error = 1;
bool fileio_append = false;

/*! \struct fileio_garbage
    \brief struct for log-file-around pointers deletions
*/
struct fileio_garbage {
	//! destructor
	~fileio_garbage() {
		free(logfilename);
		if (logfile)
			fclose(logfile);
#ifdef _MSC_VER
#ifdef DEBUG
		_CrtDumpMemoryLeaks();
#endif
#endif
	};
};

fileio_garbage garb2;

//! Observer installed by set_log_hook(); NULL when nobody is listening.
static log_hook_type surfit_log_hook = NULL;

void set_log_hook(log_hook_type hook) {
	surfit_log_hook = hook;
};

void log_printf(const char *tmplt, ...) 
{
	if (loglevel == LOG_SILENT)
		return;
	va_list ap;
	va_start (ap, tmplt);

	// Format once, so the console, the observer and the logfile all see the
	// same text.  vsnprintf keeps a long message from overrunning the buffer.
	char buf[2048];
	int written = vsnprintf(buf, sizeof(buf), tmplt, ap);
	va_end(ap);
	if (written < 0)
		return;
	if ((size_t)written >= sizeof(buf))
		written = sizeof(buf) - 1;

	// console output
	fputs(buf, stdout);
	fflush(stdout);

	if (surfit_log_hook != NULL)
		surfit_log_hook(LOG_MESSAGE, buf);

	// logfile output
	if ( (logfile) && (ferror(logfile) == 0) ) {
		fputs(buf, logfile);
		fflush(logfile);
	}

};

void writelog (int errlevel, const char *tmplt, ...) 
{
	// don't print any messages in LOG_SILENT mode
	if (loglevel == LOG_SILENT)
		return;

	// don't print messages with higher loglevel
	if (errlevel > loglevel) 
		return;

	char enter = '\n';

	struct tm * newtime;
	time_t aclock;


	time( &aclock );   // Get time in seconds
	newtime = localtime( &aclock );   // Convert time to struct tm form 

	// Print local time as a string
	char tmpbuf[128];
	strftime(tmpbuf, 128, "%d/%m/%y %H:%M:%S : ", newtime);
	console_printf("%s", tmpbuf);

	const char * prefix = "";
	switch (errlevel) {

	case LOG_MESSAGE:
		break;
	case LOG_ERROR: 
	case LOG_ERROR_TCL:
		prefix = error;
		break;
	case LOG_WARNING:
		prefix = warning;
		break;
	case LOG_DEBUG:
		prefix = debug;
		break;
	};

	// One formatting pass, shared by the console, the observer and the logfile.
	va_list ap;
	va_start (ap, tmplt);
	char buf[2048];
	int written = vsnprintf(buf, sizeof(buf), tmplt, ap);
	va_end(ap);
	if (written < 0)
		return;
	if ((size_t)written >= sizeof(buf))
		written = sizeof(buf) - 1;

	// console output: the timestamp arrived through console_printf() and the
	// severity prefix is written here.
	fputs(prefix, stdout);
	fputs(buf, stdout);
	fputc(enter, stdout);
	fflush(stdout);

	if (surfit_log_hook != NULL)
		surfit_log_hook(errlevel, buf);

	// logfile output
	if ( (logfile) && (ferror(logfile) == 0) ) {
		fwrite(tmpbuf, 1, strlen(tmpbuf), logfile);
		fputs(prefix, logfile);
		fputs(buf, logfile);
		fputc('\n', logfile);
		fflush(logfile);
	}

	if (stop_on_error == 1) {
		if (errlevel == LOG_ERROR) 
			throw "Execution stopped";
	}
};

void writelog2 (int errlevel, const char *tmplt, ...) 
{
	// don't print any messages in LOG_SILENT mode
	if (loglevel == LOG_SILENT)
		return;

	// don't print messages with higher loglevel
	if (errlevel > loglevel) 
		return;

	struct tm * newtime;
	time_t aclock;


	time( &aclock );   // Get time in seconds
	newtime = localtime( &aclock );   // Convert time to struct tm form 

	// Print local time as a string 
	char tmpbuf[128];
	strftime(tmpbuf, 128, "%d/%m/%y %H:%M:%S : ", newtime);
	console_printf("%s", tmpbuf);

	const char * prefix = "";
	switch (errlevel) {

	case LOG_MESSAGE:
		break;
	case LOG_ERROR: 
	case LOG_ERROR_TCL:
		prefix = error;
		break;
	case LOG_WARNING:
		prefix = warning;
		break;
	case LOG_DEBUG:
		prefix = debug;
		break;
	};

	// One formatting pass, shared by the console, the observer and the logfile.
	// writelog2() does not append a newline.
	va_list ap;
	va_start (ap, tmplt);
	char buf[2048];
	int written = vsnprintf(buf, sizeof(buf), tmplt, ap);
	va_end(ap);
	if (written < 0)
		return;
	if ((size_t)written >= sizeof(buf))
		written = sizeof(buf) - 1;

	// console output: see writelog().
	fputs(prefix, stdout);
	fputs(buf, stdout);
	fflush(stdout);

	if (surfit_log_hook != NULL)
		surfit_log_hook(errlevel, buf);

	// logfile output
	if ( (logfile) && (ferror(logfile) == 0) ) {
		fwrite(tmpbuf, 1, strlen(tmpbuf), logfile);
		fputs(prefix, logfile);
		fputs(buf, logfile);
		fflush(logfile);
	}

	if (stop_on_error == 1) {
		if (errlevel == LOG_ERROR) 
			throw "Execution stopped";
	}
};

void console_printf (const char *tmplt, ...) 
{
	// don't print any messages in LOG_SILENT mode
	if (loglevel == LOG_SILENT)
		return;

	va_list ap;
	va_start (ap, tmplt);

	// Console output only: no timestamp, no severity prefix, no logfile.  This
	// is what writelog() and writelog2() use for their timestamp.
	vprintf(tmplt, ap);
	fflush(stdout);

	va_end (ap);

};

int log_open(int level, const char * logname) 
{	
	loglevel = level;

	// close log if it already opened
	if (logfile) {
		fclose(logfile);
	};
	
	if (logname) {
		logfilename = strdup(logname);
	} else {
		logfilename = strdup("surfit.log");
	}
	
	logfile = fopen(logfilename, "a");
	
	if (!logfile) {
		perror("Log file open error!");
		return 0;
	}
	int err = ferror(logfile);
	if (err != 0) {
		perror("Log file open error!");
		return 0;
	};
	return 1;
};

int log_clear() 
{
	if (!logfile) {
		perror("Log file not opened!");
		return 0;
	}
	if (logfile) {
		fclose(logfile);
		logfile = fopen(logfilename, "w+");
	}
	return (logfile != NULL);
};

void putlog(const char * str) 
{
	writelog(LOG_MESSAGE, str);
};

char * read_first1024(const char * filename, int & readed) 
{
	int file = -1;
	readed = 0;
#if defined(_WIN32) || defined(__WIN32__) || defined(WIN32)
	file = open(filename, O_BINARY);
#else
	file = open(filename, O_RDONLY);
#endif
	if (file == -1) {
		writelog(LOG_ERROR, "The file %s was not opened: %s",filename,strerror( errno ));

		return NULL;
	}

	char * res = (char *) malloc(1024*sizeof(char));

	readed = read(file, res, 1024*sizeof(char));

	close(file);
	return res;
	
};

int calc_columns(const char * Str, int readed, const char * seps) 
{
	char * str = strdup(Str);

	char * pos = strchr(str, '\n');
	if (pos != NULL) {
		*pos = '\0';
	}

	pos = strchr(str, '\r');
	if (pos != NULL) {
		*pos = '\0';
	}

	int columns = 0;

	char * token = strtok( str, seps );
	while (token != NULL) {
		REAL val = (REAL)atof(token);
		if (val != 0)
			columns++;
		else {
			if (strlen(token) != 0) {
				//if ( (token[0] >= '0') && (token[0] <= '9') )
				columns++;
			}
		}
		token = strtok( NULL, seps );
	};

	free(str);
	return columns;
};

int calc_rows(const char * Str, int readed) 
{
	char * str = strdup(Str);
	char seps[] = "\n";

	int rows = 0;

	char * token = strtok( str, seps );
	while (token != NULL) {
		rows++;
		token = strtok( NULL, seps );
	}

	free(str);
	return rows;
};

char * get_name(const char * filename) 
{
	const char * posLastDot = strrchr(filename, '.');

	// check whether this dot occurs at the very beginning of a path component
	if (posLastDot != NULL) {
		if ( strchr( posLastDot, '/' ) )
			posLastDot = NULL;
	}
	if (posLastDot != NULL) {
		if ( strchr( posLastDot, '\\' ) )
			posLastDot = NULL;
	}
	if (posLastDot == filename) {
			posLastDot = NULL;
	}

	const char * posLastSlash1 = strrchr(filename, '/')+1;
	const char * posLastSlash2 = strrchr(filename, '\\')+1;
	const char * posLastSlash = MAX(posLastSlash1, posLastSlash2);
	posLastSlash = MIN(filename + strlen(filename) - 1, posLastSlash);

	const char * pos_from = MAX(filename, posLastSlash);
	const char * pos_to = posLastDot;
	if (posLastDot == NULL)
		pos_to = filename + strlen(filename);

	int len = pos_to-pos_from;

	char * res = (char *)malloc( (len+1) * sizeof(char));
	strncpy(res, pos_from, len);
	res[len]='\0';
	return res;

};

char * get_full_ext(const char * filename) 
{
	const char * search_from = filename;
	const char * posFirstDot = NULL;
	int len = strlen(filename);
	
	while (!posFirstDot) {
		posFirstDot = strchr(search_from, '.');
		if ((posFirstDot-filename) == len)
			return NULL;
		
		// check whether this dot occurs at the very beginning of a path component
		if (posFirstDot != NULL) {
			if ( strchr( posFirstDot, '/' ) ) {
				search_from = posFirstDot+1;
				posFirstDot = NULL;
			}
		}
		if (posFirstDot != NULL) {
			if ( strchr( posFirstDot, '\\' ) ) {
				search_from = posFirstDot+1;
				posFirstDot = NULL;
			}
		}
		if (posFirstDot == filename) {
			posFirstDot = NULL;
		}
	}

	const char * pos_from = posFirstDot;
	const char * pos_to = filename + strlen(filename);
	
	len = pos_to-pos_from;

	char * res = (char *)malloc( (len+1) * sizeof(char));
	strncpy(res, pos_from, len);
	res[len]='\0';
	return res;
};

char * get_ext(const char * filename) 
{
	const char * posLastDot = strrchr(filename, '.');

	// check whether this dot occurs at the very beginning of a path component
	if (posLastDot != NULL) {
		if ( strchr( posLastDot, '/' ) )
			posLastDot = NULL;
	}
	if (posLastDot != NULL) {
		if ( strchr( posLastDot, '\\' ) )
			posLastDot = NULL;
	}
	if (posLastDot == filename) {
			posLastDot = NULL;
	}

	if (posLastDot == NULL)
		return NULL;

	const char * pos_from = posLastDot;
	const char * pos_to = filename + strlen(filename);
	
	int len = pos_to-pos_from;

	char * res = (char *)malloc( (len+1) * sizeof(char));
	strncpy(res, pos_from, len);
	res[len]='\0';
	return res;
};


}; // namespace surfit;

