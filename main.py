import heapq as hq
from geopy import distance
from tools.database_connector import DatabaseConnector
from tools.vaccination_centers_scrapper import VaccCentersScraper
from tools.location_scraper import LocationsScrapper
from tools.query_creator import create_query
from tools.data_classes import VaccCenter
from config import FINAL_QUERY
from datetime import datetime
from tools.printer import print_output


def give_me_three_centers(location, vaccine=None, age_group="adult", without_registration=None, self_payer=False,
                          monday=None, tuesday=None, wednesday=None, thursday=None, friday=None, saturday=None,
                          sunday=None, update=False):
    """
    Based on specified arguments it finds and returns 3 closest vaccination centers. If update=True, it will firstly
    download the data and update the database

    Args:
      location (str): name of town in CZE.
      vaccine (str): name of wanted vaccine. Defaults to None.
      age_group (str): your age_group - "adult", "teenage", "child". Defaults to "adult".
      without_registration (bool): if you want center without registration set True. Defaults to None.
      self_payer (bool): set True if you want center for self-payers. Defaults to False.
      monday, tuesday, ... (float): specify your desired hour in the given day. Defaults to None.
      update (bool): set True if you want to download data and update the database. Defaults to False.

    Returns:
      three closest centers: list[VaccCenter]
    """
    db = DatabaseConnector(update=update)
    if update:
        _update_vacc_centers(db)
        _update_locations(db)

    query = create_query(vaccine, age_group, without_registration, self_payer, monday, tuesday, wednesday, thursday,
                         friday, saturday, sunday)
    centers_gps = db.get_data(query)
    if len(centers_gps) == 0:
        raise Exception('No centers for given input. Try different settings')
    elif len(centers_gps) <= 3:
        vacc_ids = [center[0] for center in centers_gps]
    else:
        location_gps = _get_location_gps(db, location)
        vacc_ids = calc_three_closest_centers(location_gps, centers_gps)
    final_centers = _get_vaccine_centers(db, vacc_ids)
    for center in final_centers:
        print_output(center)
    return final_centers


def calc_three_closest_centers(location: tuple, centers: list) -> list:
    """
    For location it will find 3 closest centers. For the calculation of three smallest numbers,
    we used a Heap and Heapsort thanks to its low time and space complexity.
    Function returns a list of three centers which are the closest from centre defined by coords (list[0] being the closest one)
    """
    distances = []
    for center in centers:
        distances.append(distance.distance(location, (center[1], center[2])).km)
    closest_centers = hq.nsmallest(3, distances)
    # let's now extract the index and coordinates later
    indices = [distances.index(facility) for facility in closest_centers]
    # now having the indices of the closest centres, simply return out the three closest coordinates
    result = [centers[index] for index in indices]
    return [center[0] for center in result]


def _get_vaccine_centers(db, vacc_ids: list) -> list:
    """
    based on list of vacc_ids it will download from db information about vaccination centers and store them in VaccCenter.
    Return them as list
    """
    centers = []
    for vacc_id in vacc_ids:
        query = FINAL_QUERY + f'"{vacc_id}"'
        data = db.get_data(query)[0]
        center = VaccCenter(data[1], data[2], data[3])
        center.add_open_hours({'monday': [data[4], data[5]], 'tuesday': [data[6], data[7]], 'wednesday': [data[8], data[9]],
                               'thursday': [data[10], data[11]], 'friday': [data[12], data[13]], 'saturday': [data[14], data[15]],
                               'sunday': [data[16], data[17]]})
        center.add_info({'address': data[18], 'address_spec': data[19], 'phone': data[20], 'email': data[21], 'note': data[22],
                         'vaccines': data[23], 'add_info': data[24], 'capacity': data[25], 'changing_date': data[26]})
        centers.append(center)
    return centers


def _get_location_gps(db, location: str) -> tuple:
    """
    for given location it will download its coordinates from db
    """
    query_loc = f"""
    SELECT latitude, longitude
    FROM locations
    WHERE name = "{location}"
    """
    location_gps = db.get_data(query_loc)
    if len(location_gps) == 0: raise Exception('No data for this location.')
    return location_gps[0]


def _update_vacc_centers(db):
    """
    updates data about vaccination centers
    """
    vacc_scrap = VaccCentersScraper()
    vacc_scrap.get_links()
    vacc_scrap.get_information_about_centers()
    vacc_scrap.get_gps_of_centers()
    for center in vacc_scrap.vacc_centers:
        db.insert_vacc_center(center)


def _update_locations(db):
    """
    update data about locations in CZE
    """
    loc_scrap = LocationsScrapper()
    loc_scrap.get_links()
    loc_scrap.get_gps()
    for location in loc_scrap.locations:
        db.insert_into_locations(location.name, location.gps)


if __name__ == '__main__':
    start = datetime.now()
    give_me_three_centers(update=False, vaccine="Vaxzevria")
    end = datetime.now()
    print("\n \n \n \n")
    print((end - start).total_seconds())
