-module(test_app_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_Type, _Args) ->
    {ok, Env} = application:get_env(test_app, http),
    Port = proplists:get_value(port, Env, 8080),

    ok = test_app_templates:compile_all(),
    ok = test_app_db:init(),

    Dispatch = cowboy_router:compile([
        {'_', [
            {"/",             home_handler,  []},
            {"/about",        page_handler,  [{page, about}]},
            {"/static/[...]", cowboy_static, {priv_dir, test_app, "static"}}
        ]}
    ]),

    {ok, _} = cowboy:start_clear(http_listener,
        [{port, Port}],
        #{env => #{dispatch => Dispatch}}
    ),

    error_logger:info_msg("test_app started on port ~p~n", [Port]),
    test_app_sup:start_link().

stop(_State) ->
    cowboy:stop_listener(http_listener),
    test_app_db:close(),
    ok.
