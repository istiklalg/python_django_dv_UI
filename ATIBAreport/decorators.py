
"""
@author: istiklal
"""
import gc
import logging
from datetime import datetime
from django.shortcuts import redirect

from ATIBAreport.project_common import calculate_permanent_license
from accounts.models import AtibaLicense
from django.contrib import messages

# from accounts.views import add_license

logger = logging.getLogger('commons')

"""
02/09/2021
Query for license check:

with lused  as (select unnest(ls.licenseused) lu from logsources ls  where ls.scanstatus != 9), ltotal as 
(select ald.lictypeid lid, gpd.kod lkod, sum(ald.liccount) slic from atibalicdetails ald join 
genelparametredetay gpd on ald.lictypeid=gpd.sira where gpd.kisakod='CIHAZTUR' group by lictypeid, gpd.kod), 
tot as (select gpd.ack gack,gpd.kod gkod, lu,gpd.sira, count(lu) cl from lused join genelparametredetay gpd on 
gpd.sira = lu where gpd.kisakod = 'CIHAZTUR'  group by lu, gpd.kod, gpd.ack, gpd.sira)
select ltotal.lid, ltotal.lkod, cl, ltotal.slic from tot right outer join ltotal on ltotal.lid=tot.sira

the answer is like contains 3 columns :
lid  : GeneralParameterDetail table sira column value for licdevtype value in license
lkod : GeneralParameterDetail table kod column value for licdevtype value in license
cl   : used amount of license for licdevtype
slic : limit amount in license for licdevtype
"""


def licence_required(function):
    _today = datetime.now()
    # logger.debug(f"FUNCTION : {function}")

    def wrap(request, *args, **kwargs):
        # logger.debug(f"garbage_collection_threshold : {gc.get_threshold()}")
        # logger.debug(f"Variables count pointing memory pre collection for {function.__name__} : {gc.get_count()}")
        _collected = gc.collect()
        logger.debug(f"Garbage collect operation collected : {_collected}")
        counts_for_view = gc.get_count()
        logger.info(f"Post collection count of variables that pointing memory for {function.__name__} : {counts_for_view}")
        # logger.debug(f"garbage_collection_statistics : {gc.get_stats()}")

        # if permanent license is exceeded, we need to get add_license page to work with extra parameters...
        from accounts.views import add_license

        try:
            _active_permanent_license_list = list(AtibaLicense.objects.exclude(isExpired=True).filter(
                lictype="permanent"))
            _active_temporary_license_list = list(AtibaLicense.objects.exclude(isExpired=True).filter(
                lictype="temporary"))

            _active_temporary_license = _active_temporary_license_list[0] if len(_active_temporary_license_list) > 0 else None

            _expiration = _active_temporary_license.get_license_expiration() if _active_temporary_license else None
            # print(_active_temporary_license.is_license_valid())

            if _expiration:
                if (_expiration - _today).days > 0:
                    # print(f"Demo license expiration date : {_expiration}")
                    logger.info(f"Demo license expiration date : {_expiration}")
                    try:
                        # print(f"Calling view {function.__name__}..")
                        logger.info(f"Calling view {function.__name__}..")
                        return function(request, *args, **kwargs)
                    except Exception as err:
                        # print(f"An error occurred trying to call view {function.__name__}. ERROR IS : {err}")
                        logger.exception(f"An error occurred trying to call view {function.__name__}. ERROR IS : {err}")
                        messages.error(request, f"failed to render {function.__name__}!! ERROR : {err}")
                        return redirect('check_license')
                else:
                    # print(f"Your demo license expired as of {_today} / Your expiration date : {_expiration}")
                    logger.warning(f"Your demo license expired as of {_today} / Your expiration date : {_expiration}")
                    return redirect('check_license')

            elif len(_active_permanent_license_list) > 0:
                # It means we got permanent license and no active temporary license
                logger.info(f"Not demo license, There is {len(_active_permanent_license_list)} permanent license")

                _exceed, _exceed_list = calculate_permanent_license()
                if _exceed:
                    logger.critical(f"Permanent License is Exceeded. Details : {_exceed_list}")
                    return add_license(request, exceed={"exceed": _exceed, "details": _exceed_list})
                    # pass

                try:
                    # print(f"Calling view {function.__name__}...")
                    logger.info(f"Calling view {function.__name__}...")
                    return function(request, *args, **kwargs)
                except Exception as err:
                    # print(f"An error occurred trying to call view {function.__name__}.. ERROR IS : {err}")
                    logger.exception(f"An error occurred trying to call view {function.__name__}.. ERROR IS : {err}")
                    return redirect('check_license')
            else:
                # print("NO LICENSE")
                logger.warning("NO LICENSE")
                return redirect('check_license')
        except Exception as err:
            # print(f"An error occurred trying to check license. ERROR IS : {err}")
            logger.exception(f"An error occurred trying to check license. ERROR IS : {err}")
            return redirect('check_license')

    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap
