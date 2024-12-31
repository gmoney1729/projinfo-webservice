from flask import Flask, request, jsonify
from pyproj import CRS
from pyproj.transformer import TransformerGroup
import re

def proj_string_to_list(proj_string):
    """
    Parses a proj string (including pipeline) to a list.
    Each item in the list is a separate step of the pipeline.
    Each item is a dictionary with key-value pairs for the step
    where key is the parameter name and value is the parameter value.
    """

    # Regular expression to match proj parameters taken from pyproj codebase
    # Source https://github.com/pyproj4/pyproj/blob/main/pyproj/crs/crs.py
    _RE_PROJ_PARAM = re.compile(
        r"""
        \+              # parameter starts with '+' character
        (?P<param>\w+)    # capture parameter name
        \=?             # match both key only and key-value parameters
        (?P<value>\S+)? # capture all characters up to next space (None if no value)
        \s*?            # consume remaining whitespace, if any
    """,
        re.X,
    )

    proj_list = []
    current_step = {}

    for param in _RE_PROJ_PARAM.finditer(proj_string):
        key, value = param.groups()
        if (key == "step"):
            # We are entering a new step, so save the current step (if not empty)
            # to the list and set it back to empty
            if (current_step):
                proj_list.append(current_step)
                current_step = {}
        else:
            # Otherwise, keep adding the key-value of parameters to current step
            current_step[key] = value
            
    if (current_step):
        proj_list.append(current_step)

    return proj_list


def proj_list_to_infinity_params(proj_list):
    """
    From the list of proj pipeline step(s), return those parameters
    that are supported by Infinity. If unsupported parameters are found,
    raise an exception.

    Some steps are ignored because they are inherently supported by Infinity
    and not needed to define the coordinate system. These include changing the
    order of 
    """

    # proj steps that are not relevant to Infinity
    ignored_steps = {"push", "pop", "unitconvert", "axisswap", "pipeline", "cart"}

    # list of projection types supported by Infinity
    supported_proj = {"merc", "tmerc", "omerc", "utm", "cass", "lcc", "stere", "sterea"}

    # Helmert transformations with velocity parameters that are not supported
    helmert_unsupported_params = {"dx", "dy", "dz", "drx", "dry", "drz", "ds", "t_epoch"}

    infinity_params = {"proj": {}, "trf": {}}  # Projection and transformation parameters for Infinity

    for step in proj_list:
        if (step["proj"] in ignored_steps):
            continue
        if (step["proj"] in supported_proj):
            for key in step:
                infinity_params["proj"][key] = step[key]
        elif (step["proj"] == "helmert"):
            # Check if there are velocity parameters in the Helmert transformation step
            if(step.keys() & helmert_unsupported_params):
                raise NotImplementedError("Unsupported velocity based Helmert transformation")
            for key in step:
                infinity_params["trf"][key] = step[key]
        else:
            raise NotImplementedError("Unsupported projection type parameter")
        
    return infinity_params


# Initialize Flask app
app = Flask(__name__)

@app.route('/transform', methods=['GET'])
def get_crs_transform():
    """
    Returns the proj conversion string from WGS84 to provided EPSG code along with some metadata.
    """
    try:
        target_epsg = request.args.get('epsg', type=int)
        if not target_epsg:
            return jsonify({"error": "Target EPSG code is required as a query parameter."}), 400

        transformerGroup = TransformerGroup(4326, target_epsg)
        if (transformerGroup == None) or (len(transformerGroup.transformers) == 0):
            return jsonify({"error": "No transformation available to the given EPSG code."}), 400

        transformer = transformerGroup.transformers[0]
        proj_string = transformer.to_proj4()
        crs = CRS.from_epsg(target_epsg)

        return jsonify({
            "source_epsg": 4326,
            "target_epsg": target_epsg,
            "proj4": proj_string,
            "name": crs.name,
            "datum": crs.datum.name,
            "conversion_description": transformer.description,
            "area_of_use": crs.area_of_use.name,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/infinityparams', methods=['GET'])
def get_infinity_params():
    """
    Get projection and transformation parameters supported by Infinity given the EPSG code.
    """
    try:
        target_epsg = request.args.get('epsg', type=int)
        if not target_epsg:
            return jsonify({"error": "Target EPSG code is required as a query parameter."}), 400

        transformerGroup = TransformerGroup(4326, target_epsg)
        if (transformerGroup == None) or (len(transformerGroup.transformers) == 0):
            return jsonify({"error": "No transformation available to the given EPSG code."}), 400

        transformer = transformerGroup.transformers[0]
        proj_string = transformer.to_proj4()
        crs = CRS.from_epsg(target_epsg)
        proj_list = proj_string_to_list(proj_string)
        infinity_params = proj_list_to_infinity_params(proj_list)

        return jsonify({
            "source_epsg": 4326,
            "target_epsg": target_epsg,
            "name": crs.name,
            "datum": crs.datum.name,
            "conversion_description": transformer.description,
            "area_of_use": crs.area_of_use.name,
            "infinity_params": infinity_params
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Entry point for Vercel
if __name__ != "__main__":
    # Allow Vercel to detect and serve the app
    app = app

# # Run app locally
# if __name__ == "__main__":
#     app.run(debug=True)