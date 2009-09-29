#include <Python.h>
#include <string.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#ifndef __user
#define __user
#endif
#include <sys/types.h>
#include <linux/types.h>
#include <sys/socket.h>
#include <net/if.h>
#include <wireless.h>

/************************ CONSTANTS & MACROS ************************/

/*
 * Constants fof WE-9->15
 */
#define IW15_MAX_FREQUENCIES	16
#define IW15_MAX_BITRATES	8
#define IW15_MAX_TXPOWER	8
#define IW15_MAX_ENCODING_SIZES	8
#define IW15_MAX_SPY		8
#define IW15_MAX_AP		8

/*
 *  Struct iw_range up to WE-15
 */
struct  iw15_range
{
    __u32       throughput;
    __u32       min_nwid;
    __u32       max_nwid;
    __u16       num_channels;
    __u8        num_frequency;
    struct iw_freq  freq[IW15_MAX_FREQUENCIES];
    __s32       sensitivity;
    struct iw_quality   max_qual;
    __u8        num_bitrates;
    __s32       bitrate[IW15_MAX_BITRATES];
    __s32       min_rts;
    __s32       max_rts;
    __s32       min_frag;
    __s32       max_frag;
    __s32       min_pmp;
    __s32       max_pmp;
    __s32       min_pmt;
    __s32       max_pmt;
    __u16       pmp_flags;
    __u16       pmt_flags;
    __u16       pm_capa;
    __u16       encoding_size[IW15_MAX_ENCODING_SIZES];
    __u8        num_encoding_sizes;
    __u8        max_encoding_tokens;
    __u16       txpower_capa;
    __u8        num_txpower;
    __s32       txpower[IW15_MAX_TXPOWER];
    __u8        we_version_compiled;
    __u8        we_version_source;
    __u16       retry_capa;
    __u16       retry_flags;
    __u16       r_time_flags;
    __s32       min_retry;
    __s32       max_retry;
    __s32       min_r_time;
    __s32       max_r_time;
    struct iw_quality   avg_qual;
};

/*
 * Union for all the versions of iwrange.
 * Fortunately, I mostly only add fields at the end, and big-bang
 * reorganisations are few.
 */
union   iw_range_raw
{
    struct iw15_range   range15;    /* WE 9->15 */
    struct iw_range     range;      /* WE 16->current */
};

/*
 * Offsets in iw_range struct
 */
#define iwr15_off(f)    ( ((char *) &(((struct iw15_range *) NULL)->f)) - \
              (char *) NULL)
#define iwr_off(f)  ( ((char *) &(((struct iw_range *) NULL)->f)) - \
              (char *) NULL)

typedef struct iw_range		iwrange;

/*------------------------------------------------------------------*/
/*
 * Wrapper to extract some Wireless Parameter out of the driver
 */
static inline int
iw_get_ext(int			skfd,		/* Socket to the kernel */
	   const char *		ifname,		/* Device name */
	   int			request,	/* WE ID */
	   struct iwreq *	pwrq)		/* Fixed part of the request */
{
  /* Set device name */
  strncpy(pwrq->ifr_name, ifname, IFNAMSIZ);
  /* Do the request */
  return(ioctl(skfd, request, pwrq));
}
/*------------------------------------------------------------------*/
/*
 * Get the range information out of the driver
 */
int
iw_get_range_info(int skfd, const char *ifname, iwrange * range)
{
  struct iwreq      wrq;
  char          buffer[sizeof(iwrange) * 2];    /* Large enough */
  union iw_range_raw *  range_raw;

  /* Cleanup */
  bzero(buffer, sizeof(buffer));

  wrq.u.data.pointer = (caddr_t) buffer;
  wrq.u.data.length = sizeof(buffer);
  wrq.u.data.flags = 0;
  if(iw_get_ext(skfd, ifname, SIOCGIWRANGE, &wrq) < 0)
    return(-1);

  /* Point to the buffer */
  range_raw = (union iw_range_raw *) buffer;

  /* For new versions, we can check the version directly, for old versions
   * we use magic. 300 bytes is a also magic number, don't touch... */
  if(wrq.u.data.length < 300)
    {
      /* That's v10 or earlier. Ouch ! Let's make a guess...*/
      range_raw->range.we_version_compiled = 9;
    }

  /* Check how it needs to be processed */
  if(range_raw->range.we_version_compiled > 15)
    {
      /* This is our native format, that's easy... */
      /* Copy stuff at the right place, ignore extra */
      memcpy((char *) range, buffer, sizeof(iwrange));
    }
  else
    {
      /* Zero unknown fields */
      bzero((char *) range, sizeof(struct iw_range));

      /* Initial part unmoved */
      memcpy((char *) range,
         buffer,
         iwr15_off(num_channels));
      /* Frequencies pushed futher down towards the end */
      memcpy((char *) range + iwr_off(num_channels),
         buffer + iwr15_off(num_channels),
         iwr15_off(sensitivity) - iwr15_off(num_channels));
      /* This one moved up */
      memcpy((char *) range + iwr_off(sensitivity),
         buffer + iwr15_off(sensitivity),
         iwr15_off(num_bitrates) - iwr15_off(sensitivity));
      /* This one goes after avg_qual */
      memcpy((char *) range + iwr_off(num_bitrates),
         buffer + iwr15_off(num_bitrates),
         iwr15_off(min_rts) - iwr15_off(num_bitrates));
      /* Number of bitrates has changed, put it after */
      memcpy((char *) range + iwr_off(min_rts),
         buffer + iwr15_off(min_rts),
         iwr15_off(txpower_capa) - iwr15_off(min_rts));
      /* Added encoding_login_index, put it after */
      memcpy((char *) range + iwr_off(txpower_capa),
         buffer + iwr15_off(txpower_capa),
         iwr15_off(txpower) - iwr15_off(txpower_capa));
      /* Hum... That's an unexpected glitch. Bummer. */
      memcpy((char *) range + iwr_off(txpower),
         buffer + iwr15_off(txpower),
         iwr15_off(avg_qual) - iwr15_off(txpower));
      /* Avg qual moved up next to max_qual */
      memcpy((char *) range + iwr_off(avg_qual),
         buffer + iwr15_off(avg_qual),
         sizeof(struct iw_quality));
    }

  return(0);
}

static PyObject *
    get_max_quality(PyObject *self, PyObject *args)
{
    const char *iface;
    int max_quality;
    int fd, err;
    struct iw_range range;

    if (!PyArg_ParseTuple(args, "s", &iface))
        return NULL;

    fd = socket (PF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        fprintf (stderr, "couldn't open socket\n");
        return NULL;
    }

    err = iw_get_range_info(fd, iface, &range);
    close (fd);

    if (err < 0) {
        PyErr_SetFromErrno(PyExc_IOError);
        return NULL;
    }
    max_quality = range.max_qual.qual;
    return Py_BuildValue("i", max_quality);
}

/* python module details */
static PyMethodDef net_monitor_Methods[] = {
    {"get_max_quality", get_max_quality, METH_VARARGS,
        "Find maximum quality value for a wireless interface."},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

PyMODINIT_FUNC
initnet_monitor(void)
{
    (void) Py_InitModule("net_monitor", net_monitor_Methods);
}

