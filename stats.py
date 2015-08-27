#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import errno
import re
import subprocess
import rrdtool
import sqlite3

'''Path to rrd files.'''
rrdpath = "/var/www/web/stats/rrd"
'''Path to store images.'''
rrdgraphs = "/var/www/web/stats/img"
'''Path to store sqlite db file. If you have high io load it will be beter to store file in tmpfs.'''
dbpath = "/dev/shm"


def check_dir(path):
    '''Create directories if not exist.'''
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


check_dir(rrdpath)
check_dir(rrdgraphs)

'''Sqlite db connect and create tables for cpu and hdd statistics.'''
db = sqlite3.connect(dbpath + '/stats.db')
db_cursor = db.cursor()
db_cursor.execute('''
                  CREATE TABLE IF NOT EXISTS cpu(id INTEGER PRIMARY KEY, user INTEGER, nice INTEGER,
                  system INTEGER, idle INTEGER, iowait INTEGER, irq INTEGER,
                  softirq INTEGER, steal INTEGER)
                  ''')
db.commit()

db_cursor.execute('''
                  CREATE TABLE IF NOT EXISTS hdd(drive TEXT PRIMARY KEY, r_issued INTEGER, r_merged INTEGER,
                  r_sectors INTEGER, r_time INTEGER, w_completed INTEGER, w_merged INTEGER,
                  w_sectors INTEGER, w_time INTEGER, io_inprogress INTEGER, io_time INTEGER, io_total_time INTEGER)
                  ''')
db.commit()

# ############################################################NETWORK##########################################################################


def get_network_stats(interface):
    '''Getting statistics for network interface from file /proc/net/dev'''
    for line in open('/proc/net/dev', 'r'):
        if interface in line:
            data = line.split('%s:' % interface)[1].split()
            rx_bytes = data[0]
            rx_packets = data[1]
            rx_errors = data[2]
            rx_drops = data[3]
            tx_bytes = data[8]
            tx_packets = data[9]
            tx_errors = data[10]
            tx_drops = data[11]
            return (int(rx_bytes), int(rx_packets), int(rx_errors), int(rx_drops), int(tx_bytes), int(tx_packets), int(tx_errors), int(tx_drops))

rx_bytes, rx_packets, rx_errors, rx_drops, tx_bytes, tx_packets, tx_errors, tx_drops = get_network_stats('eth0')

'''Interface bits/s. Update RRD file, create daily,weekly,monthly,yearly graphs or create RRD file if not exists.'''
if os.path.isfile(rrdpath + '/if-traffic.rrd'):
    rrdtool.update(rrdpath + '/if-traffic.rrd', 'N:%s:%s' % (rx_bytes, tx_bytes))
    for sched in ['daily', 'weekly', 'monthly', 'yearly']:
        if sched == 'weekly':
            period = 'w'
        elif sched == 'daily':
            period = 'd'
        elif sched == 'monthly':
            period = 'm'
        elif sched == 'yearly':
            period = 'y'
        rrdtool.graph(rrdgraphs + '/traffic-%s.png' % (sched), '--imgformat', 'PNG',
                      '--start', '-1%s' % (period), '--title', 'Traffic', '--rigid', '--base',
                      '1000', '--height', '120', '--width', '500', '--alt-autoscale-max',
                      '--lower-limit', '0', '--vertical-label', 'bits per second', '--slope-mode',
                      'DEF:a=%s/if-traffic.rrd:traffic_in:AVERAGE' % (rrdpath),
                      'DEF:b=%s/if-traffic.rrd:traffic_out:AVERAGE' % (rrdpath),
                      'CDEF:cdefa=a,8,*', 'CDEF:cdefe=b,8,*',
                      'AREA:cdefa#00CF00FF:Inbound', 'GPRINT:cdefa:LAST:Current\:%8.2lf %s',
                      'GPRINT:cdefa:AVERAGE:Average\:%8.2lf %s', 'GPRINT:cdefa:MAX:Maximum\:%8.2lf %s\\n',
                      'LINE1:cdefe#002A97FF:Outbound', 'GPRINT:cdefe:LAST:Current\:%8.2lf %s',
                      'GPRINT:cdefe:AVERAGE:Average\:%8.2lf %s', 'GPRINT:cdefe:MAX:Maximum\:%8.2lf %s\\n')
else:
    rrdtool.create(rrdpath + '/if-traffic.rrd', '--step', '300',
                   'DS:traffic_in:COUNTER:600:0:1000000000', 'DS:traffic_out:COUNTER:600:0:1000000000',
                   'RRA:AVERAGE:0.5:1:500', 'RRA:AVERAGE:0.5:1:600', 'RRA:AVERAGE:0.5:6:700',
                   'RRA:AVERAGE:0.5:24:775', 'RRA:AVERAGE:0.5:288:797', 'RRA:MAX:0.5:1:500',
                   'RRA:MAX:0.5:1:600', 'RRA:MAX:0.5:6:700', 'RRA:MAX:0.5:24:775', 'RRA:MAX:0.5:288:797')

'''Interface packets/s. Update RRD file, create daily,weekly,monthly,yearly graphs or create RRD file if not exists.'''
if os.path.isfile(rrdpath + '/if-packets.rrd'):
    rrdtool.update(rrdpath + '/if-packets.rrd', 'N:%s:%s' % (rx_packets, tx_packets))
    for sched in ['daily', 'weekly', 'monthly', 'yearly']:
        if sched == 'weekly':
            period = 'w'
        elif sched == 'daily':
            period = 'd'
        elif sched == 'monthly':
            period = 'm'
        elif sched == 'yearly':
            period = 'y'
        rrdtool.graph(rrdgraphs + '/packets-%s.png' % (sched), '--imgformat', 'PNG',
                      '--start', '-1%s' % (period), '--title', 'Unicast Packets', '--rigid', '--base',
                      '1000', '--height', '120', '--width', '500', '--alt-autoscale-max',
                      '--lower-limit', '0', '--vertical-label', 'packets/sec', '--slope-mode',
                      'DEF:a=%s/if-packets.rrd:unicast_in:AVERAGE' % (rrdpath),
                      'DEF:b=%s/if-packets.rrd:unicast_out:AVERAGE' % (rrdpath),
                      'AREA:a#FFF200FF:Unicast Packets In', 'GPRINT:a:LAST:Current\:%8.2lf %s',
                      'GPRINT:a:AVERAGE:Average\:%8.2lf %s', 'GPRINT:a:MAX:Maximum\:%8.2lf %s\\n',
                      'LINE1:b#00234BFF:Unicast Packets Out', 'GPRINT:b:LAST:Current\:%8.2lf %s',
                      'GPRINT:b:AVERAGE:Average\:%8.2lf %s', 'GPRINT:b:MAX:Maximum\:%8.2lf %s\\n')
else:
    rrdtool.create(rrdpath + '/if-packets.rrd', '--step', '300',
                   'DS:unicast_in:COUNTER:600:0:700000', 'DS:unicast_out:COUNTER:600:0:700000',
                   'RRA:AVERAGE:0.5:1:500', 'RRA:AVERAGE:0.5:1:600', 'RRA:AVERAGE:0.5:6:700',
                   'RRA:AVERAGE:0.5:24:775', 'RRA:AVERAGE:0.5:288:797', 'RRA:MAX:0.5:1:500',
                   'RRA:MAX:0.5:1:600', 'RRA:MAX:0.5:6:700', 'RRA:MAX:0.5:24:775', 'RRA:MAX:0.5:288:797')

'''Interface errors and drops. Update RRD file, create daily,weekly,monthly,yearly graphs or create RRD file if not exists.'''
if os.path.isfile(rrdpath + '/if-errors.rrd'):
    rrdtool.update(rrdpath + '/if-errors.rrd', 'N:%s:%s:%s:%s' % (rx_errors, rx_drops, tx_errors, tx_drops,))
    for sched in ['daily', 'weekly', 'monthly', 'yearly']:
        if sched == 'weekly':
            period = 'w'
        elif sched == 'daily':
            period = 'd'
        elif sched == 'monthly':
            period = 'm'
        elif sched == 'yearly':
            period = 'y'
        rrdtool.graph(rrdgraphs + '/errors-%s.png' % (sched), '--imgformat', 'PNG',
                      '--start', '-1%s' % (period), '--title', 'Errors', '--rigid', '--base',
                      '1000', '--height', '120', '--width', '500', '--alt-autoscale-max',
                      '--lower-limit', '0', '--vertical-label', 'errors/sec', '--slope-mode',
                      'DEF:a=%s/if-errors.rrd:discards_in:AVERAGE' % (rrdpath),
                      'DEF:b=%s/if-errors.rrd:errors_in:AVERAGE' % (rrdpath),
                      'DEF:c=%s/if-errors.rrd:discards_out:AVERAGE' % (rrdpath),
                      'DEF:d=%s/if-errors.rrd:errors_out:AVERAGE' % (rrdpath),
                      'LINE1:a#FFAB00FF:Discards In', 'GPRINT:a:LAST:Current\:%8.2lf %s',
                      'GPRINT:a:AVERAGE:Average\:%8.2lf %s', 'GPRINT:a:MAX:Maximum\:%8.2lf %s\\n',
                      'LINE1:b#F51D30FF:Errors In', 'GPRINT:b:LAST:Current\:%8.2lf %s',
                      'GPRINT:b:AVERAGE:Average\:%8.2lf %s', 'GPRINT:b:MAX:Maximum\:%8.2lf %s\\n',
                      'LINE1:c#C4FD3DFF:Discards Out', 'GPRINT:c:LAST:Current\:%8.2lf %s',
                      'GPRINT:c:AVERAGE:Average\:%8.2lf %s', 'GPRINT:c:MAX:Maximum\:%8.2lf %s\\n',
                      'LINE1:d#00694AFF:Errors Out', 'GPRINT:d:LAST:Current\:%8.2lf %s',
                      'GPRINT:d:AVERAGE:Average\:%8.2lf %s', 'GPRINT:d:MAX:Maximum\:%8.2lf %s\\n')
else:
    rrdtool.create(rrdpath + '/if-errors.rrd', '--step', '300',
                   'DS:errors_in:COUNTER:600:0:1000000000', 'DS:discards_in:COUNTER:600:0:1000000000',
                   'DS:errors_out:COUNTER:600:0:1000000000', 'DS:discards_out:COUNTER:600:0:1000000000',
                   'RRA:AVERAGE:0.5:1:500', 'RRA:AVERAGE:0.5:1:600', 'RRA:AVERAGE:0.5:6:700',
                   'RRA:AVERAGE:0.5:24:775', 'RRA:AVERAGE:0.5:288:797', 'RRA:MAX:0.5:1:500',
                   'RRA:MAX:0.5:1:600', 'RRA:MAX:0.5:6:700', 'RRA:MAX:0.5:24:775', 'RRA:MAX:0.5:288:797')

# #############################################################################################################################################################################################

# #########################################################MEMORY USAGE#######################################################################################################################


def get_mem_usage():
    '''Getting memory usage from command gree -b'''
    run = subprocess.check_output(['free', '-b'])
    mem = run.split()
    total = int(mem[7])
    used = int(mem[8])
    free = int(mem[9])
    shared = int(mem[10])
    buffers = int(mem[11])
    cached = int(mem[12])
    totalsw = int(mem[18])
    usedsw = int(mem[19])
    freesw = int(mem[20])
    return (total, used, free, shared, buffers, cached, totalsw, usedsw, freesw)

total, used, free, shared, buffers, cached, totalsw, usedsw, freesw = get_mem_usage()

'''Memory usage. Update RRD file, create daily,weekly,monthly,yearly graphs or create RRD file if not exists.'''
if os.path.isfile(rrdpath + '/memory.rrd'):
    rrdtool.update(rrdpath + '/memory.rrd', 'N:%s:%s:%s:%s:%s:%s' % (total, used, free, shared, buffers, cached))
    for sched in ['daily', 'weekly', 'monthly', 'yearly']:
        if sched == 'weekly':
            period = 'w'
        elif sched == 'daily':
            period = 'd'
        elif sched == 'monthly':
            period = 'm'
        elif sched == 'yearly':
            period = 'y'
        rrdtool.graph(rrdgraphs + '/memory-%s.png' % (sched), '--imgformat', 'PNG',
                      '--start', '-1%s' % (period), '--title', 'Memory Usage', '--rigid', '--base',
                      '1000', '--height', '120', '--width', '500', '--alt-autoscale-max',
                      '--lower-limit', '0', '--vertical-label', 'bytes', '--slope-mode',
                      'DEF:a=%s/memory.rrd:memtotal:AVERAGE' % (rrdpath),
                      'DEF:b=%s/memory.rrd:memused:AVERAGE' % (rrdpath),
                      'DEF:c=%s/memory.rrd:memfree:AVERAGE' % (rrdpath),
                      'DEF:d=%s/memory.rrd:memshared:AVERAGE' % (rrdpath),
                      'DEF:e=%s/memory.rrd:membuffers:AVERAGE' % (rrdpath),
                      'DEF:f=%s/memory.rrd:memcached:AVERAGE' % (rrdpath),
                      'CDEF:cdefa=b,d,-,e,-,f,-',
                      'AREA:cdefa#FF0000FF:User', 'GPRINT:cdefa:LAST:Current\:%8.2lf %s',
                      'GPRINT:cdefa:AVERAGE:Average\:%8.2lf %s', 'GPRINT:cdefa:MIN:Min\:%8.2lf %s',
                      'GPRINT:cdefa:MAX:Max\:%8.2lf %s\\n',
                      'AREA:e#6EA100FF:Buffers:STACK', 'GPRINT:e:LAST:Current\:%8.2lf %s',
                      'GPRINT:e:AVERAGE:Average\:%8.2lf %s', 'GPRINT:e:MIN:Min\:%8.2lf %s',
                      'GPRINT:e:MAX:Max\:%8.2lf %s\\n',
                      'AREA:f#FFF200FF:Cached:STACK', 'GPRINT:f:LAST:Current\:%8.2lf %s',
                      'GPRINT:f:AVERAGE:Average\:%8.2lf %s', 'GPRINT:f:MIN:Min\:%8.2lf %s',
                      'GPRINT:f:MAX:Max\:%8.2lf %s\\n',
                      'AREA:c#12B3B5FF:Free:STACK', 'GPRINT:c:LAST:Current\:%8.2lf %s',
                      'GPRINT:c:AVERAGE:Average\:%8.2lf %s', 'GPRINT:c:MIN:Min\:%8.2lf %s',
                      'GPRINT:c:MAX:Max\:%8.2lf %s\\n',
                      'LINE1:a#000000FF:Total', 'GPRINT:a:MAX:Current\:%8.2lf %s\\n')
else:
    rrdtool.create(rrdpath + '/memory.rrd', '--step', '300',
                   'DS:memtotal:GAUGE:600:0:U', 'DS:memused:GAUGE:600:0:U',
                   'DS:memfree:GAUGE:600:0:U', 'DS:memshared:GAUGE:600:0:U',
                   'DS:membuffers:GAUGE:600:0:U', 'DS:memcached:GAUGE:600:0:U',
                   'RRA:AVERAGE:0.5:1:500', 'RRA:AVERAGE:0.5:1:600', 'RRA:AVERAGE:0.5:6:700',
                   'RRA:AVERAGE:0.5:24:775', 'RRA:AVERAGE:0.5:288:797', 'RRA:MAX:0.5:1:500',
                   'RRA:MAX:0.5:1:600', 'RRA:MAX:0.5:6:700', 'RRA:MAX:0.5:24:775', 'RRA:MAX:0.5:288:797')

'''Swap usage. Update RRD file, create daily,weekly,monthly,yearly graphs or create RRD file if not exists.'''
if os.path.isfile(rrdpath + '/swap.rrd'):
    rrdtool.update(rrdpath + '/swap.rrd', 'N:%s:%s:%s' % (totalsw, usedsw, freesw))
    for sched in ['daily', 'weekly', 'monthly', 'yearly']:
        if sched == 'weekly':
            period = 'w'
        elif sched == 'daily':
            period = 'd'
        elif sched == 'monthly':
            period = 'm'
        elif sched == 'yearly':
            period = 'y'
        rrdtool.graph(rrdgraphs + '/swap-%s.png' % (sched), '--imgformat', 'PNG',
                      '--start', '-1%s' % (period), '--title', 'Swap Usage', '--rigid', '--base',
                      '1000', '--height', '120', '--width', '500', '--alt-autoscale-max',
                      '--lower-limit', '0', '--vertical-label', 'bytes', '--slope-mode',
                      'DEF:a=%s/swap.rrd:swaptotal:AVERAGE' % (rrdpath),
                      'DEF:b=%s/swap.rrd:swapused:AVERAGE' % (rrdpath),
                      'DEF:c=%s/swap.rrd:swapfree:AVERAGE' % (rrdpath),
                      'AREA:b#FF0000FF:Used', 'GPRINT:b:LAST:Current\:%8.2lf %s',
                      'GPRINT:b:AVERAGE:Average\:%8.2lf %s', 'GPRINT:b:MIN:Min\:%8.2lf %s',
                      'GPRINT:b:MAX:Max\:%8.2lf %s\\n',
                      'AREA:c#12B3B5FF:Free:STACK', 'GPRINT:c:LAST:Current\:%8.2lf %s',
                      'GPRINT:c:AVERAGE:Average\:%8.2lf %s', 'GPRINT:c:MIN:Min\:%8.2lf %s',
                      'GPRINT:c:MAX:Max\:%8.2lf %s\\n',
                      'LINE1:a#000000FF:Total', 'GPRINT:a:MAX:Current\:%8.2lf %s\\n')
else:
    rrdtool.create(rrdpath + '/swap.rrd', '--step', '300',
                   'DS:swaptotal:GAUGE:600:0:U', 'DS:swapused:GAUGE:600:0:U', 'DS:swapfree:GAUGE:600:0:U',
                   'RRA:AVERAGE:0.5:1:500', 'RRA:AVERAGE:0.5:1:600', 'RRA:AVERAGE:0.5:6:700',
                   'RRA:AVERAGE:0.5:24:775', 'RRA:AVERAGE:0.5:288:797', 'RRA:MAX:0.5:1:500',
                   'RRA:MAX:0.5:1:600', 'RRA:MAX:0.5:6:700', 'RRA:MAX:0.5:24:775', 'RRA:MAX:0.5:288:797')
# #############################################################################################################################################################################################

# ######################################################################################DISK USAGE#############################################################################################


def get_disks():
    '''Getting all sd[a-z] disks'''
    diskstats = open('/proc/diskstats', 'r')
    diskstats_r = diskstats.read()
    diskstats.close()
    disks = re.findall('sd[a-z][ ]', diskstats_r)
    disks = [x.strip(' ') for x in disks]
    return disks


def get_disk_stats(disk):
    '''Getting io  statistics for each disks'''
    for line in open('/proc/diskstats', 'r'):
        if disk in line:
            data = line.split('%s' % disk)[1].split()
            r_issued = data[0]
            r_merged = data[1]
            r_sectors = data[2]
            r_time = data[3]
            w_completed = data[4]
            w_merged = data[5]
            w_sectors = data[6]
            w_time = data[7]
            io_inprogress = data[8]
            io_time = data[9]
            io_total_time = data[10]
            return (int(r_issued), int(r_merged), int(r_sectors), int(r_time), int(w_completed), int(w_merged), int(w_sectors), int(w_time), int(io_inprogress), int(io_time), int(io_total_time))


def get_prev_disk_stats(disk):
    '''Getting previous disk statistics from sqlite db. If previous statistics doesn't exist, set previous data = current data.'''
    db_cursor.execute('''SELECT * from hdd WHERE drive=?''', (disk,))
    prev_data = db_cursor.fetchall()
    if len(prev_data) == 0:
        prev_r_issued, prev_r_merged, prev_r_sectors, prev_r_time, prev_w_completed, prev_w_merged, prev_w_sectors, prev_w_time, prev_io_inprogress, prev_io_time, prev_io_total_time = get_disk_stats(disk)
    else:
        for row in prev_data:
            prev_r_issued = int(row[1])
            prev_r_merged = int(row[2])
            prev_r_sectors = int(row[3])
            prev_r_time = int(row[4])
            prev_w_completed = int(row[5])
            prev_w_merged = int(row[6])
            prev_w_sectors = int(row[7])
            prev_w_time = int(row[8])
            prev_io_inprogress = int(row[9])
            prev_io_time = int(row[10])
            prev_io_total_time = int(row[11])
    return (prev_r_issued, prev_r_merged, prev_r_sectors, prev_r_time, prev_w_completed, prev_w_merged, prev_w_sectors, prev_w_time, prev_io_inprogress, prev_io_time, prev_io_total_time)


def get_disk_usage():
    '''Getting usage of / partition'''
    run = subprocess.check_output(['df', '-k'])
    part = run.split()
    partidx = part.index('/')
    totalidx = partidx - 4
    usedidx = partidx - 3
    disk_total = part[totalidx]
    disk_used = part[usedidx]
    return (int(disk_total), int(disk_used))

disk_total, disk_used = get_disk_usage()

'''Root partition usage. Update RRD file, create daily,weekly,monthly,yearly graphs or create RRD file if not exists.'''
if os.path.isfile(rrdpath + '/disk-space.rrd'):
    rrdtool.update(rrdpath + '/disk-space.rrd', 'N:%s:%s' % (disk_total, disk_used))
    for sched in ['daily', 'weekly', 'monthly', 'yearly']:
        if sched == 'weekly':
            period = 'w'
        elif sched == 'daily':
            period = 'd'
        elif sched == 'monthly':
            period = 'm'
        elif sched == 'yearly':
            period = 'y'
        rrdtool.graph(rrdgraphs + '/disk-space-%s.png' % (sched), '--imgformat', 'PNG',
                      '--start', '-1%s' % (period), '--title', 'Used Space', '--rigid', '--base',
                      '1000', '--height', '120', '--width', '500', '--alt-autoscale-max',
                      '--lower-limit', '0', '--vertical-label', 'bytes', '--slope-mode',
                      'DEF:a=%s/disk-space.rrd:total:AVERAGE' % (rrdpath),
                      'DEF:b=%s/disk-space.rrd:used:AVERAGE' % (rrdpath),
                      'CDEF:cdefa=a,1024,*',
                      'CDEF:cdefb=b,1024,*',
                      'AREA:cdefa#002A97FF:Total', 'GPRINT:cdefa:LAST:Current\:%8.2lf %s',
                      'GPRINT:cdefa:AVERAGE:Average\:%8.2lf %s', 'GPRINT:cdefa:MAX:Maximum\:%8.2lf %s\\n',
                      'AREA:cdefb#F51D30FF:Used', 'GPRINT:cdefb:LAST:Current\:%8.2lf %s',
                      'GPRINT:cdefb:AVERAGE:Average\:%8.2lf %s', 'GPRINT:cdefb:MAX:Maximum\:%8.2lf %s\\n')
else:
        rrdtool.create(rrdpath + '/disk-space.rrd', '--step', '300',
                       'DS:total:GAUGE:600:0:U', 'DS:used:GAUGE:600:0:U',
                       'RRA:AVERAGE:0.5:1:500', 'RRA:AVERAGE:0.5:1:600', 'RRA:AVERAGE:0.5:6:700',
                       'RRA:AVERAGE:0.5:24:775', 'RRA:AVERAGE:0.5:288:797', 'RRA:MAX:0.5:1:500',
                       'RRA:MAX:0.5:1:600', 'RRA:MAX:0.5:6:700', 'RRA:MAX:0.5:24:775', 'RRA:MAX:0.5:288:797')

for disk in get_disks():
    '''Getting current and previous io stats for each disks and calculation delta's'''
    r_issued, r_merged, r_sectors, r_time, w_completed, w_merged, w_sectors, w_time, io_inprogress, io_time, io_total_time = get_disk_stats(disk)
    prev_r_issued, prev_r_merged, prev_r_sectors, prev_r_time, prev_w_completed, prev_w_merged, prev_w_sectors, prev_w_time, prev_io_inprogress, prev_io_time, prev_io_total_time = get_prev_disk_stats(disk)
    delta_io_total_time = float(io_total_time - prev_io_total_time)
    delta_io_time = float(io_time - prev_io_time)
    delta_r_time = float(r_time - prev_r_time)
    delta_w_time = float(w_time - prev_w_time)
    delta_r_issued = float(r_issued - prev_r_issued)
    delta_w_completed = float(w_completed - prev_w_completed)
    if delta_io_total_time == 0 or delta_io_time == 0:
        avgqsz = 0
        await = 0
    else:
        avgqsz = delta_io_total_time / delta_io_time
        await = (delta_r_time + delta_w_time) / (delta_r_issued + delta_w_completed)
    '''Updating io stats in sqlite db'''
    db_cursor.execute('''
                      INSERT OR IGNORE INTO hdd (drive) VALUES (?)
                      ''', (disk,))
    db.commit()
    db_cursor.execute('''
                      UPDATE hdd SET r_issued = ?, r_merged = ?, r_sectors = ?, r_time = ?, w_completed = ?, w_merged = ?, w_sectors = ?, w_time = ?, io_inprogress = ?, io_time = ?, io_total_time = ? WHERE drive=?
                      ''', (r_issued, r_merged, r_sectors, r_time, w_completed, w_merged, w_sectors, w_time, io_inprogress, io_time, io_total_time, disk))
    db.commit()

    '''IO load. Update RRD file, create daily,weekly,monthly,yearly graphs or create RRD file if not exists.'''
    if os.path.isfile(rrdpath + '/disk-io-load-'+disk+'.rrd'):
        rrdtool.update(rrdpath + '/disk-io-load-'+disk+'.rrd', 'N:%s:%s' % (avgqsz, await))
        for sched in ['daily', 'weekly', 'monthly', 'yearly']:
            if sched == 'weekly':
                period = 'w'
            elif sched == 'daily':
                period = 'd'
            elif sched == 'monthly':
                period = 'm'
            elif sched == 'yearly':
                period = 'y'
            rrdtool.graph(rrdgraphs + '/disk-io-load-%s-%s.png' % (disk, sched), '--imgformat', 'PNG',
                          '--start', '-1%s' % (period), '--title', 'Avg queue size and wait time - %s' % (disk), '--rigid', '--base',
                          '1000', '--height', '120', '--width', '500', '--alt-autoscale-max',
                          '--lower-limit', '0', '--vertical-label', 'Avg queue/time', '--slope-mode',
                          'DEF:a=%s/disk-io-load-%s.rrd:avgqsz:AVERAGE' % (rrdpath, disk),
                          'DEF:b=%s/disk-io-load-%s.rrd:await:AVERAGE' % (rrdpath, disk),
                          'LINE2:a#0000FFFF:Avg queue size', 'GPRINT:a:LAST:Current\:%8.2lf %s',
                          'GPRINT:a:AVERAGE:Average\:%8.2lf %s', 'GPRINT:a:MAX:Maximum\:%8.2lf %s\\n',
                          'LINE2:b#FF0000FF:Avg wait time', 'GPRINT:b:LAST:Current\:%8.2lf %s',
                          'GPRINT:b:AVERAGE:Average\:%8.2lf %s', 'GPRINT:b:MAX:Maximum\:%8.2lf %s\\n')
    else:
        rrdtool.create(rrdpath + '/disk-io-load-'+disk+'.rrd', '--step', '300',
                       'DS:avgqsz:GAUGE:600:0:U', 'DS:await:GAUGE:600:0:U',
                       'RRA:AVERAGE:0.5:1:500', 'RRA:AVERAGE:0.5:1:600', 'RRA:AVERAGE:0.5:6:700',
                       'RRA:AVERAGE:0.5:24:775', 'RRA:AVERAGE:0.5:288:797', 'RRA:MAX:0.5:1:500',
                       'RRA:MAX:0.5:1:600', 'RRA:MAX:0.5:6:700', 'RRA:MAX:0.5:24:775', 'RRA:MAX:0.5:288:797')

    '''IO stats tps. Update RRD file, create daily,weekly,monthly,yearly graphs or create RRD file if not exists.'''
    if os.path.isfile(rrdpath + '/disk-io-'+disk+'.rrd'):
        rrdtool.update(rrdpath + '/disk-io-'+disk+'.rrd', 'N:%s:%s' % (r_issued, w_completed))
        for sched in ['daily', 'weekly', 'monthly', 'yearly']:
            if sched == 'weekly':
                period = 'w'
            elif sched == 'daily':
                period = 'd'
            elif sched == 'monthly':
                period = 'm'
            elif sched == 'yearly':
                period = 'y'
            rrdtool.graph(rrdgraphs + '/disk-io-%s-%s.png' % (disk, sched), '--imgformat', 'PNG',
                          '--start', '-1%s' % (period), '--title', 'IO Stats - %s' % (disk), '--rigid', '--base',
                          '1000', '--height', '120', '--width', '500', '--alt-autoscale-max',
                          '--lower-limit', '0', '--vertical-label', 'io per second', '--slope-mode',
                          'DEF:a=%s/disk-io-%s.rrd:io_reads:AVERAGE' % (rrdpath, disk),
                          'DEF:b=%s/disk-io-%s.rrd:io_writes:AVERAGE' % (rrdpath, disk),
                          'LINE2:a#0000FFFF:Reads', 'GPRINT:a:LAST:Current\:%8.2lf %s',
                          'GPRINT:a:AVERAGE:Average\:%8.2lf %s', 'GPRINT:a:MAX:Maximum\:%8.2lf %s\\n',
                          'LINE2:b#FF0000FF:Writes', 'GPRINT:b:LAST:Current\:%8.2lf %s',
                          'GPRINT:b:AVERAGE:Average\:%8.2lf %s', 'GPRINT:b:MAX:Maximum\:%8.2lf %s\\n')
    else:
        rrdtool.create(rrdpath + '/disk-io-'+disk+'.rrd', '--step', '300',
                       'DS:io_reads:COUNTER:600:0:100000', 'DS:io_writes:COUNTER:600:0:100000',
                       'RRA:AVERAGE:0.5:1:500', 'RRA:AVERAGE:0.5:1:600', 'RRA:AVERAGE:0.5:6:700',
                       'RRA:AVERAGE:0.5:24:775', 'RRA:AVERAGE:0.5:288:797', 'RRA:MAX:0.5:1:500',
                       'RRA:MAX:0.5:1:600', 'RRA:MAX:0.5:6:700', 'RRA:MAX:0.5:24:775', 'RRA:MAX:0.5:288:797')

    '''IO stats bps. Update RRD file, create daily,weekly,monthly,yearly graphs or create RRD file if not exists.'''
    if os.path.isfile(rrdpath + '/disk-io-sectors-'+disk+'.rrd'):
        rrdtool.update(rrdpath + '/disk-io-sectors-'+disk+'.rrd', 'N:%s:%s' % (r_sectors, w_sectors))
        for sched in ['daily', 'weekly', 'monthly', 'yearly']:
            if sched == 'weekly':
                period = 'w'
            elif sched == 'daily':
                period = 'd'
            elif sched == 'monthly':
                period = 'm'
            elif sched == 'yearly':
                period = 'y'
            rrdtool.graph(rrdgraphs + '/disk-io-sectors-%s-%s.png' % (disk, sched), '--imgformat', 'PNG',
                          '--start', '-1%s' % (period), '--title', 'Bytes R/W - %s' % (disk), '--rigid', '--base',
                          '1000', '--height', '120', '--width', '500', '--alt-autoscale-max',
                          '--lower-limit', '0', '--vertical-label', 'Bytes Read/Written', '--slope-mode',
                          'DEF:a=%s/disk-io-sectors-%s.rrd:sectors_reads:AVERAGE' % (rrdpath, disk),
                          'DEF:b=%s/disk-io-sectors-%s.rrd:sectors_writes:AVERAGE' % (rrdpath, disk),
                          'CDEF:cdefa=a,512,*',
                          'CDEF:cdefb=b,512,*',
                          'LINE3:cdefa#55D6D3FF:Bytes Read', 'GPRINT:cdefa:LAST:Current\:%8.2lf %s',
                          'GPRINT:cdefa:AVERAGE:Average\:%8.2lf %s', 'GPRINT:cdefa:MAX:Maximum\:%8.2lf %s\\n',
                          'LINE3:cdefb#FFAB00FF:Bytes Written', 'GPRINT:cdefb:LAST:Current\:%8.2lf %s',
                          'GPRINT:cdefb:AVERAGE:Average\:%8.2lf %s', 'GPRINT:cdefb:MAX:Maximum\:%8.2lf %s\\n')
    else:
        rrdtool.create(rrdpath + '/disk-io-sectors-'+disk+'.rrd', '--step', '300',
                       'DS:sectors_reads:COUNTER:600:0:2000000', 'DS:sectors_writes:COUNTER:600:0:2000000',
                       'RRA:AVERAGE:0.5:1:500', 'RRA:AVERAGE:0.5:1:600', 'RRA:AVERAGE:0.5:6:700',
                       'RRA:AVERAGE:0.5:24:775', 'RRA:AVERAGE:0.5:288:797', 'RRA:MAX:0.5:1:500',
                       'RRA:MAX:0.5:1:600', 'RRA:MAX:0.5:6:700', 'RRA:MAX:0.5:24:775', 'RRA:MAX:0.5:288:797')

# ##############################################################################################################################################################################################

# ############################################################CPU USAGE##########################################################################


def get_cur_cpu_stats():
    '''Getting cpu stats from file /proc/stat'''
    for line in open('/proc/stat', 'r'):
        if 'cpu ' in line:
            data = line.split('cpu ')[1].split()
            cur_t_user = int(data[0])
            cur_t_nice = int(data[1])
            cur_t_system = int(data[2])
            cur_t_idle = int(data[3])
            cur_t_iowait = int(data[4])
            cur_t_irq = int(data[5])
            cur_t_softirq = int(data[6])
            cur_t_steal = int(data[7])
            return (cur_t_user, cur_t_nice, cur_t_system, cur_t_idle, cur_t_iowait, cur_t_irq, cur_t_softirq, cur_t_steal)


def get_prev_cpu_stats():
    '''Getting previous cpu stats from sqlite. If previous stats doesn't exist, previous stats = current stats'''
    db_cursor.execute('''SELECT * from cpu WHERE id=1''')
    prev_data = db_cursor.fetchall()
    if len(prev_data) == 0:
        prev_t_user, prev_t_nice, prev_t_system, prev_t_idle, prev_t_iowait, prev_t_irq, prev_t_softirq, prev_t_steal = get_cur_cpu_stats()
    else:
        for row in prev_data:
            prev_t_user = int(row[1])
            prev_t_nice = int(row[2])
            prev_t_system = int(row[3])
            prev_t_idle = int(row[4])
            prev_t_iowait = int(row[5])
            prev_t_irq = int(row[6])
            prev_t_softirq = int(row[7])
            prev_t_steal = int(row[8])
    return (prev_t_user, prev_t_nice, prev_t_system, prev_t_idle, prev_t_iowait, prev_t_irq, prev_t_softirq, prev_t_steal)

cur_t_user, cur_t_nice, cur_t_system, cur_t_idle, cur_t_iowait, cur_t_irq, cur_t_softirq, cur_t_steal = get_cur_cpu_stats()
prev_t_user, prev_t_nice, prev_t_system, prev_t_idle, prev_t_iowait, prev_t_irq, prev_t_softirq, prev_t_steal = get_prev_cpu_stats()
cur_t_total = cur_t_user + cur_t_nice + cur_t_system + cur_t_idle + cur_t_iowait + cur_t_irq + cur_t_softirq + cur_t_steal
prev_t_total = prev_t_user + prev_t_nice + prev_t_system + prev_t_idle + prev_t_iowait + prev_t_irq + prev_t_softirq + prev_t_steal
delta_t_total = float(cur_t_total-prev_t_total)
delta_t_user = float(cur_t_user-prev_t_user)
delta_t_nice = float(cur_t_nice-prev_t_nice)
delta_t_system = float(cur_t_system-prev_t_system)
delta_t_idle = float(cur_t_idle-prev_t_idle)
delta_t_iowait = float(cur_t_iowait-prev_t_iowait)
delta_t_irq = float(cur_t_irq-prev_t_irq)
delta_t_softirq = float(cur_t_softirq-prev_t_softirq)
delta_t_steal = float(cur_t_steal-prev_t_steal)
if delta_t_total == 0:
    cpu_total = 0
    cpu_user = 0
    cpu_nice = 0
    cpu_system = 0
    cpu_idle = 0
    cpu_iowait = 0
    cpu_irq = 0
    cpu_softirq = 0
    cpu_steal = 0
else:
    cpu_total = ((delta_t_total-delta_t_idle)/delta_t_total)*100
    cpu_user = ((delta_t_total-delta_t_nice-delta_t_system-delta_t_idle-delta_t_iowait-delta_t_irq-delta_t_softirq-delta_t_steal)/delta_t_total)*100
    cpu_nice = ((delta_t_total-delta_t_user-delta_t_system-delta_t_idle-delta_t_iowait-delta_t_irq-delta_t_softirq-delta_t_steal)/delta_t_total)*100
    cpu_system = ((delta_t_total-delta_t_user-delta_t_nice-delta_t_idle-delta_t_iowait-delta_t_irq-delta_t_softirq-delta_t_steal)/delta_t_total)*100
    cpu_idle = ((delta_t_total-delta_t_user-delta_t_nice-delta_t_system-delta_t_iowait-delta_t_irq-delta_t_softirq-delta_t_steal)/delta_t_total)*100
    cpu_iowait = ((delta_t_total-delta_t_user-delta_t_nice-delta_t_system-delta_t_idle-delta_t_irq-delta_t_softirq-delta_t_steal)/delta_t_total)*100
    cpu_irq = ((delta_t_total-delta_t_user-delta_t_nice-delta_t_system-delta_t_idle-delta_t_iowait-delta_t_softirq-delta_t_steal)/delta_t_total)*100
    cpu_softirq = ((delta_t_total-delta_t_user-delta_t_nice-delta_t_system-delta_t_idle-delta_t_iowait-delta_t_irq-delta_t_steal)/delta_t_total)*100
    cpu_steal = ((delta_t_total-delta_t_user-delta_t_nice-delta_t_system-delta_t_idle-delta_t_iowait-delta_t_irq-delta_t_softirq)/delta_t_total)*100

db_cursor.execute('''
                  INSERT OR IGNORE INTO cpu (id) VALUES (1)
                  ''')
db.commit()
db_cursor.execute('''
                  UPDATE cpu SET user = ?, nice = ?, system = ?, idle = ?, iowait = ?, irq = ?, softirq = ?, steal = ? WHERE id=1
                  ''', (cur_t_user, cur_t_nice, cur_t_system, cur_t_idle, cur_t_iowait, cur_t_irq, cur_t_softirq, cur_t_steal))
db.commit()
'''
print 'Previous: ', prev_t_user, prev_t_nice, prev_t_system, prev_t_idle, prev_t_iowait, prev_t_irq, prev_t_softirq, prev_t_steal, prev_t_total
print 'Current: ', cur_t_user, cur_t_nice, cur_t_system, cur_t_idle, cur_t_iowait, cur_t_irq, cur_t_softirq, cur_t_steal, cur_t_total
print 'Cpu Total %: ', cpu_total
print 'Cpu User %: ', cpu_user
print 'Cpu Nice %: ', cpu_nice
print 'Cpu System %: ', cpu_system
print 'Cpu Idle %: ', cpu_idle
print 'Cpu Iowait %: ', cpu_iowait
print 'Cpu Irq %: ', cpu_irq
print 'Cpu Softirq %: ', cpu_softirq
print 'Cpu Steal %: ', cpu_steal
'''

'''CPU usage. Update RRD file, create daily,weekly,monthly,yearly graphs or create RRD file if not exists.'''
if os.path.isfile(rrdpath + '/cpu.rrd'):
    rrdtool.update(rrdpath + '/cpu.rrd', 'N:%s:%s:%s:%s:%s:%s:%s:%s:%s' % (cpu_user, cpu_nice, cpu_system, cpu_idle, cpu_iowait, cpu_irq, cpu_softirq, cpu_steal, cpu_total))
    for sched in ['daily', 'weekly', 'monthly', 'yearly']:
        if sched == 'weekly':
            period = 'w'
        elif sched == 'daily':
            period = 'd'
        elif sched == 'monthly':
            period = 'm'
        elif sched == 'yearly':
            period = 'y'
        rrdtool.graph(rrdgraphs + '/cpu-%s.png' % (sched), '--imgformat', 'PNG',
                      '--start', '-1%s' % (period), '--title', 'CPU Usage', '--rigid', '--base',
                      '1000', '--height', '120', '--width', '500', '--alt-autoscale-max',
                      '--lower-limit', '0', '--vertical-label', 'percents', '--slope-mode',
                      'DEF:a=%s/cpu.rrd:user:AVERAGE' % (rrdpath),
                      'DEF:b=%s/cpu.rrd:nice:AVERAGE' % (rrdpath),
                      'DEF:c=%s/cpu.rrd:system:AVERAGE' % (rrdpath),
                      'DEF:d=%s/cpu.rrd:idle:AVERAGE' % (rrdpath),
                      'DEF:e=%s/cpu.rrd:iowait:AVERAGE' % (rrdpath),
                      'DEF:f=%s/cpu.rrd:irq:AVERAGE' % (rrdpath),
                      'DEF:g=%s/cpu.rrd:softirq:AVERAGE' % (rrdpath),
                      'DEF:h=%s/cpu.rrd:steal:AVERAGE' % (rrdpath),
                      'DEF:i=%s/cpu.rrd:total:AVERAGE' % (rrdpath),
                      'AREA:c#FF0000FF:System', 'GPRINT:c:LAST:Current\:%8.2lf %s',
                      'GPRINT:c:AVERAGE:Average\:%8.2lf %s', 'GPRINT:c:MAX:Maximum\:%8.2lf %s\\n',
                      'AREA:f#0000FFFF:Interrupts:STACK', 'GPRINT:f:LAST:Current\:%8.2lf %s',
                      'GPRINT:f:AVERAGE:Average\:%8.2lf %s', 'GPRINT:f:MAX:Maximum\:%8.2lf %s\\n',
                      'AREA:g#4668E4FF:Soft Interrupts:STACK', 'GPRINT:g:LAST:Current\:%8.2lf %s',
                      'GPRINT:g:AVERAGE:Average\:%8.2lf %s', 'GPRINT:g:MAX:Maximum\:%8.2lf %s\\n',
                      'AREA:e#00BED9FF:Wait:STACK', 'GPRINT:e:LAST:Current\:%8.2lf %s',
                      'GPRINT:e:AVERAGE:Average\:%8.2lf %s', 'GPRINT:e:MAX:Maximum\:%8.2lf %s\\n',
                      'AREA:a#F5F800FF:User:STACK', 'GPRINT:a:LAST:Current\:%8.2lf %s',
                      'GPRINT:a:AVERAGE:Average\:%8.2lf %s', 'GPRINT:a:MAX:Maximum\:%8.2lf %s\\n',
                      'AREA:b#00FF00FF:Nice:STACK', 'GPRINT:b:LAST:Current\:%8.2lf %s',
                      'GPRINT:b:AVERAGE:Average\:%8.2lf %s', 'GPRINT:b:MAX:Maximum\:%8.2lf %s\\n',
                      'LINE1:i#000000FF:Total', 'GPRINT:i:LAST:Current\:%8.2lf %s',
                      'GPRINT:i:AVERAGE:Average\:%8.2lf %s', 'GPRINT:i:MAX:Maximum\:%8.2lf %s\\n',
                      'LINE1:d#FFFFFF00:Idle', 'GPRINT:d:LAST:Current\:%8.2lf %s',
                      'GPRINT:d:AVERAGE:Average\:%8.2lf %s', 'GPRINT:d:MAX:Maximum\:%8.2lf %s\\n')
else:
    rrdtool.create(rrdpath + '/cpu.rrd', '--step', '300',
                   'DS:user:GAUGE:600:0:U', 'DS:nice:GAUGE:600:0:U',
                   'DS:system:GAUGE:600:0:U', 'DS:idle:GAUGE:600:0:U',
                   'DS:iowait:GAUGE:600:0:U', 'DS:irq:GAUGE:600:0:U',
                   'DS:softirq:GAUGE:600:0:U', 'DS:steal:GAUGE:600:0:U',
                   'DS:total:GAUGE:600:0:U',
                   'RRA:AVERAGE:0.5:1:500', 'RRA:AVERAGE:0.5:1:600', 'RRA:AVERAGE:0.5:6:700',
                   'RRA:AVERAGE:0.5:24:775', 'RRA:AVERAGE:0.5:288:797', 'RRA:MAX:0.5:1:500',
                   'RRA:MAX:0.5:1:600', 'RRA:MAX:0.5:6:700', 'RRA:MAX:0.5:24:775', 'RRA:MAX:0.5:288:797')

# ##############################################################################################################################################################################################

db.close()
