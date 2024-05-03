from flask_parameter_validation import ValidateParameters, Query

import boardlib.api.aurora
import flask
import requests

import climbdex.db

blueprint = flask.Blueprint("api", __name__)

def param_error_handler(err):
    return {
        "error": True,
        "details": str(err),
        "message": f"There was an issue getting results. If the issue persists please <a href=\"https://github.com/lemeryfertitta/Climbdex/issues/new?title={str(err)}\" target='_blank'>report it</a>"
    }, 400


@blueprint.route("/api/v1/<board_name>/layouts")
def layouts(board_name):
    return flask.jsonify(climbdex.db.get_data(board_name, "layouts"))


@blueprint.route("/api/v1/<board_name>/layouts/<layout_id>/sizes")
def sizes(board_name, layout_id):
    return flask.jsonify(
        climbdex.db.get_data(board_name, "sizes", {"layout_id": int(layout_id)})
    )


@blueprint.route("/api/v1/<board_name>/layouts/<layout_id>/sizes/<size_id>/sets")
def sets(board_name, layout_id, size_id):
    return flask.jsonify(
        climbdex.db.get_data(
            board_name, "sets", {"layout_id": int(layout_id), "size_id": int(size_id)}
        )
    )


@blueprint.route("/api/v1/search/count")
@ValidateParameters(param_error_handler)
def resultsCount(
    gradeAccuracy: float = Query(),
    layout: int = Query(),
    maxGrade: int = Query(),
    minAscents: int = Query(),
    minGrade: int = Query(),
    minRating: float = Query(),
    size: int = Query(),
):
    return flask.jsonify(climbdex.db.get_search_count(flask.request.args))


@blueprint.route("/api/v1/search")
@ValidateParameters(param_error_handler)
def search(
    gradeAccuracy: float = Query(),
    layout: int = Query(),
    maxGrade: int = Query(),
    minAscents: int = Query(),
    minGrade: int = Query(),
    minRating: float = Query(),
    size: int = Query(),
):
    return flask.jsonify(climbdex.db.get_search_results(flask.request.args))


@blueprint.route("/api/v1/<board_name>/beta/<uuid>")
def beta(board_name, uuid):
    return flask.jsonify(climbdex.db.get_data(board_name, "beta", {"uuid": uuid}))


@blueprint.route("/api/v1/login/", methods=["POST"])
def login():
    try:
        login_details = boardlib.api.aurora.login(
            flask.request.json["board"],
            flask.request.json["username"],
            flask.request.json["password"],
        )
        return flask.jsonify(
            {"token": login_details["token"], "user_id": login_details["user_id"]}
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == requests.codes.unprocessable_entity:
            return (
                flask.jsonify({"error": "Invalid username/password combination"}),
                e.response.status_code,
            )
        else:
            return flask.jsonify({"error": str(e)}), e.response.status_code
