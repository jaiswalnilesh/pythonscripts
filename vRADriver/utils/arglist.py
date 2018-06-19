from optparse import OptionParser
from vRADriver.utils.filesystem import get_config_value

def parse_options(args):

    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)

    parser.add_option("-t", "--catalogName",
                    dest="catn",
                    default=get_config_value(configs, 'CATLNAME'),
                    help="Name of the catalog that includes the"
                        " application container template.")
    parser.add_option("-v", "--vdcName",
                    dest="vdcn",
                    default=get_config_value(configs, 'VDCNAME'),
                    help="Name of MSC Product"
                        " i.e Nastran or Patran.")
    parser.add_option("-u", "--vmName",
                    dest="vmn",
                    default=get_config_value(configs, 'VMNAME'),
                    help="Valid virtual machine name")
    parser.add_option("-s", "--durationHours",
                    dest="durh",
                    default=get_config_value(configs, 'DURHRS'),
                    help="Time duration, until VM is active, optional")
    parser.add_option("-b", "--beginTime",
                    dest="begt",
                    default=get_config_value(configs, 'BEGINTIME'),
                    help="Start time fo VM usage")
    parser.add_option("-q", "--quantity",
                    dest="qty",
                    default=get_config_value(configs, 'QUANTITY'),
                    help="No. of VM for subscription, presently support only 1")
    parser.add_option("-m", "--memoryMB",
                    dest="mem",
                    default=get_config_value(configs, 'MEMORY'),
                    help="Memory to be used for VM")
    parser.add_option("-c", "--cores",
                    dest="core",
                    default=get_config_value(configs, 'CORE'),
                    help="Core to be used for VM")
    parser.add_option("-e", "--estimatedCost",
                    dest="estc",
                    default=get_config_value(configs, 'ESTIMATECOST'),
                    help="Cost of VM")
    parser.add_option("-r", "--comments",
                    dest="comm",
                    default=get_config_value(configs, 'COMMENTS'),
                    help="Provide your remarks")
    parser.add_option("-i", "--additionalInfo",
                    dest="addinfo",
                    default=get_config_value(configs, 'ADDINFO'),
                    help="More information")
    parser.add_option("-d", "--debug",
                    action="store_true", dest="debug",
                    default=get_config_value(configs, 'DEBUG', False),
                    help="display debug output")
    parser.add_option("-f", "--runtime_dir",
                    dest="runtdir",
                    default=get_config_value(configs, 'RUNTIME_DIR'),
                    help="Runtime directory path")
    (globals()["options"], args) = parser.parse_args(args)

    if options.debug:
        # create logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to logger
        logger.addHandler(ch)

    return args

