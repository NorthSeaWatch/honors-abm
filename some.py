import csv
def add_ports():
        """Add ports to the model with their coordinates"""
        
        ports_data = []
        with open('/Users/abartashevich/Desktop/honors-abm/src/data/filtered_port.csv', 'r') as csv_file_port:
                reader_port = csv.DictReader(csv_file_port)
                for row in reader_port:
                    port = {
                    "id": int(row["INDEX_NO"]),
                    "name": row["PORT_NAME"],
                    "pos_x": float(row["LATITUDE"]),
                    "pos_y": float(row["LONGITUDE"]),
                    "capacity": row["HARBORSIZE"]}
                    ports_data.append(port)
    
        return ports_data

print(len(add_ports()))