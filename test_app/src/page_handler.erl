-module(page_handler).
-behaviour(cowboy_handler).
-export([init/2]).

init(Req, State) ->
    Page     = proplists:get_value(page, State, not_found),
    Template = atom_to_list(Page) ++ ".html",
    Title    = page_title(Page),
    Req2     = test_app_handler:render(Req, Template, #{title => Title}),
    {ok, Req2, State}.

page_title(about)   -> <<"About">>;
page_title(contact) -> <<"Contact">>;
page_title(_)       -> <<"Page">>.
