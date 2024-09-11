import boardlib.api.aurora
import flask
import climbdex.db
import json
import pandas

blueprint = flask.Blueprint("view", __name__)


@blueprint.route("/")
def index():
    return flask.render_template(
        "boardSelection.html.j2",
    )


@blueprint.route("/filter")
def filter():
    board_name = flask.request.args.get("board")
    layout_id = flask.request.args.get("layout")
    size_id = flask.request.args.get("size")
    set_ids = flask.request.args.getlist("set")
    return flask.render_template(
        "filterSelection.html.j2",
        params=flask.request.args,
        board_name=board_name,
        layout_name=climbdex.db.get_data(
            board_name, "layout_name", {"layout_id": layout_id}
        )[0][0],
        size_name=climbdex.db.get_data(
            board_name, "size_name", {"layout_id": layout_id, "size_id": size_id}
        )[0][0],
        angles=climbdex.db.get_data(board_name, "angles", {"layout_id": layout_id}),
        grades=climbdex.db.get_data(board_name, "grades"),
        setters=climbdex.db.get_data(board_name, "setters", {"layout_id": layout_id}),
        colors=climbdex.db.get_data(board_name, "colors", {"layout_id": layout_id}),
        **get_draw_board_kwargs(board_name, layout_id, size_id, set_ids),
    )


@blueprint.route("/results")
def results():
    board_name = flask.request.args.get("board")
    layout_id = flask.request.args.get("layout")
    size_id = flask.request.args.get("size")
    set_ids = flask.request.args.getlist("set")
    login_cookie = flask.request.cookies.get(f"{board_name}_login")
    ticked_climbs = get_ticked_climbs(board_name, login_cookie) if login_cookie else []
    attempted_climbs = get_bids(board_name, login_cookie) if login_cookie else []
    placement_positions = get_placement_positions(board_name, layout_id, size_id)
    return flask.render_template(
        "results.html.j2",
        app_url=boardlib.api.aurora.WEB_HOSTS[board_name],
        colors=climbdex.db.get_data(board_name, "colors", {"layout_id": layout_id}),
        ticked_climbs=ticked_climbs,
        attempted_climbs=attempted_climbs,
        placement_positions=placement_positions,
        grades=climbdex.db.get_data(board_name, "grades"),
        led_colors=get_led_colors(board_name, layout_id),
        layout_is_mirrored=climbdex.db.layout_is_mirrored(board_name,layout_id),
        login_cookie=login_cookie,
        **get_draw_board_kwargs(
            board_name,
            layout_id,
            size_id,
            set_ids,
        ),
    )


@blueprint.route("/<board_name>/beta/<uuid>")
def beta(board_name, uuid):
    beta = climbdex.db.get_data(board_name, "beta", {"uuid": uuid})
    climb_name = climbdex.db.get_data(board_name, "climb", {"uuid": uuid})[0][0]
    return flask.render_template(
        "beta.html.j2",
        beta=beta,
        climb_name=climb_name,
    )


@blueprint.route("/create")
def create():
    board_name = flask.request.args.get("board")
    layout_id = flask.request.args.get("layout")
    size_id = flask.request.args.get("size")
    set_ids = flask.request.args.getlist("set")
    colors = climbdex.db.get_data(board_name, "colors", {"layout_id": layout_id})
    app_url = boardlib.api.aurora.WEB_HOSTS[board_name]
    placement_positions = get_placement_positions(board_name, layout_id, size_id)
    return flask.render_template(
        "climbCreation.html.j2",
        app_url=app_url,
        board=board_name,
        layout_name=climbdex.db.get_data(
            board_name, "layout_name", {"layout_id": layout_id}
        )[0][0],
        size_name=climbdex.db.get_data(
            board_name, "size_name", {"layout_id": layout_id, "size_id": size_id}
        )[0][0],
        colors=colors,
        led_colors=get_led_colors(board_name, layout_id),
        placement_positions=placement_positions,
        **get_draw_board_kwargs(board_name, layout_id, size_id, set_ids),
    )


def get_draw_board_kwargs(board_name, layout_id, size_id, set_ids):
    images_to_holds = {}
    for set_id in set_ids:
        image_filename = climbdex.db.get_data(
            board_name,
            "image_filename",
            {"layout_id": layout_id, "size_id": size_id, "set_id": set_id},
        )[0][0]
        image_url = f"{boardlib.api.aurora.API_HOSTS[board_name]}/img/{image_filename}"
        images_to_holds[image_url] = climbdex.db.get_data(
            board_name, "holds", {"layout_id": layout_id, "set_id": set_id}
        )

    size_dimensions = climbdex.db.get_data(
        board_name, "size_dimensions", {"size_id": size_id}
    )[0]
    return {
        "images_to_holds": images_to_holds,
        "edge_left": size_dimensions[0],
        "edge_right": size_dimensions[1],
        "edge_bottom": size_dimensions[2],
        "edge_top": size_dimensions[3],
    }


def get_ticked_climbs(board, login_cookie):
    login_info = flask.json.loads(login_cookie)
    logbook = boardlib.api.aurora.get_logbook(
        board, login_info["token"], login_info["user_id"]
    )
    ticked_climbs = {}
    normal_tick = 0
    mirror_tick = 1
    both_tick = 2
    for log in logbook:
        key = f'{log["climb_uuid"]}-{log["angle"]}'
        tick_type = mirror_tick if log["is_mirror"] else normal_tick
        existing_tick = ticked_climbs.get(key)
        ticked_climbs[key] = (
            both_tick
            if existing_tick is not None and existing_tick != tick_type
            else tick_type
        )
    return ticked_climbs


def get_bids(board, login_cookie):
    db_path = f"data/{board}/db.sqlite3"
    login_info = json.loads(login_cookie)
    full_logbook_df = boardlib.api.aurora.logbook_entries(
        board, token=login_info["token"], user_id=login_info["user_id"], db_path=db_path
    )

    if full_logbook_df.empty:
        return pandas.DataFrame(
            columns=[
                "climb_angle_uuid",
                "board",
                "climb_name",
                "date",
                "sessions",
                "tries",
            ]
        )

    aggregated_logbook = (
        full_logbook_df.groupby(["climb_angle_uuid", "board", "climb_name"])
        .agg(
            date=("date", "max"),
            sessions=("climb_angle_uuid", "count"),
            tries=("tries", "sum"),
        )
        .reset_index()
    )

    aggregated_logbook["date"] = aggregated_logbook["date"].dt.strftime("%d/%m/%Y")

    aggregated_json = aggregated_logbook.to_dict(orient="records")
    formatted_json = {
        entry["climb_angle_uuid"]: {
            "total_tries": entry["tries"],
            "total_sessions": entry["sessions"],
            "last_try": entry["date"],
        }
        for entry in aggregated_json
    }

    return formatted_json


def get_placement_positions(board_name, layout_id, size_id):
    binds = {"layout_id": layout_id, "size_id": size_id}
    return {
        placement_id: position
        for placement_id, position in climbdex.db.get_data(board_name, "leds", binds)
    }


def get_led_colors(board_name, layout_id):
    binds = {"layout_id": layout_id}
    return {
        role_id: color
        for role_id, color in climbdex.db.get_data(board_name, "led_colors", binds)
    }
