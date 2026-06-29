%%% Shared handler utilities.
-module(test_app_handler).

-export([render/3, reply_json/3, reply_error/3, not_found/1, base_ctx/1]).

render(Req, Template, Ctx) ->
    Mod     = test_app_templates:template_module(
                  filename:join(["priv/templates", Template])),
    FullCtx = maps:merge(base_ctx(Req), Ctx),
    case Mod:render(FullCtx) of
        {ok, Iolist} ->
            cowboy_req:reply(200,
                #{<<"content-type">> => <<"text/html; charset=utf-8">>},
                Iolist, Req);
        {error, Reason} ->
            error_logger:error_msg("[handler] template ~p error: ~p~n",
                                   [Template, Reason]),
            reply_error(Req, 500, <<"Template rendering failed">>)
    end.

reply_json(Req, Status, Data) ->
    cowboy_req:reply(Status,
        #{<<"content-type">> => <<"application/json; charset=utf-8">>},
        jsone:encode(Data), Req).

reply_error(Req, Status, Message) ->
    case error_dtl:render(#{status => Status, message => Message}) of
        {ok, Html} ->
            cowboy_req:reply(Status,
                #{<<"content-type">> => <<"text/html; charset=utf-8">>},
                Html, Req);
        _ ->
            cowboy_req:reply(Status,
                #{<<"content-type">> => <<"text/plain">>},
                Message, Req)
    end.

not_found(Req) -> reply_error(Req, 404, <<"Page not found">>).

base_ctx(Req) ->
    {Y, _, _} = date(),
    #{path     => cowboy_req:path(Req),
      app_name => <<"test_app">>,
      year     => integer_to_binary(Y)}.
