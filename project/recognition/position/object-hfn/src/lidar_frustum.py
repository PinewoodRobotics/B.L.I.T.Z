from dataclasses import asdict, dataclass
import json
import requests

@dataclass
class Point3D:
    x: float;
    y: float;
    z: float;

    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @staticmethod
    def from_json(json_str: str):
        data = json.loads(json_str)
        return Point3D(**data)


class LidarPointsFrustum:
    def __init__(self, port: int):
        self.port = port;
        pass

    def get_frustum_points(self, origin: Point3D, other: list[Point3D]) -> list[Point3D] | None:
        headers = {
            "Content-Type": "application/json"
        }

        json = {
            "origin": {
                "x": origin.x,
                "y": origin.y,
                "z": origin.z
            },
            "directions": [
                {
                    "x": other[0].x,
                    "y": other[0].y,
                    "z": other[0].z
                },
                {
                    "x": other[1].x,
                    "y": other[1].y,
                    "z": other[1].z
                },
                {
                    "x": other[2].x,
                    "y": other[2].y,
                    "z": other[2].z
                },
                {
                    "x": other[3].x,
                    "y": other[3].y,
                    "z": other[3].z
                },
            ]
        }

        response = requests.post("http://localhost:" + str(self.port) + "/post-json", json=json, headers=headers)

        json_res = response.json()
        if json_res == None or "points" not in json_res:
            return None

        pts: list[Point3D] = []
        for i in json_res["points"]:
            pts.append(Point3D(i["x"], i["y"], i["z"]))

        return pts