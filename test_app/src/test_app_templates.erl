-module(test_app_templates).

-export([compile_all/0, compile/1, template_module/1]).

compile_all() ->
    Dir   = template_dir(),
    Files = filelib:wildcard("**/*.html", Dir),
    case Files of
        [] ->
            error_logger:warning_msg("[templates] No .html files in ~s~n", [Dir]),
            ok;
        _ ->
            Results = [compile(filename:join(Dir, F)) || F <- Files],
            Errors  = [E || E <- Results, E =/= ok],
            case Errors of
                [] ->
                    error_logger:info_msg("[templates] Compiled ~p file(s)~n",
                                         [length(Files)]),
                    ok;
                _ ->
                    error({template_compile_errors, Errors})
            end
    end.

compile(Path) ->
    AbsPath = filename:absname(Path),
    Mod     = template_module(AbsPath),
    OutDir  = code:lib_dir(test_app, ebin),
    DocRoot = template_dir(),

    Opts = [
        {doc_root,         DocRoot},
        {out_dir,          OutDir},
        {module,           Mod},
        {compiler_options, [debug_info]},
        return
    ],

    error_logger:info_msg("[templates] Compiling ~s as ~p~n", [AbsPath, Mod]),

    code:soft_purge(Mod),
    code:delete(Mod),

    case erlydtl:compile_file(AbsPath, Mod, Opts) of
        {ok, Mod} ->
            load_from_disk(Mod, OutDir);
        {ok, Mod, Warnings} ->
            [error_logger:warning_msg("[templates] ~s: ~p~n", [AbsPath, W])
             || W <- Warnings],
            load_from_disk(Mod, OutDir);
        {error, Errors, _} ->
            error_logger:error_msg("[templates] ERROR ~s:~n~p~n", [AbsPath, Errors]),
            {error, AbsPath, Errors}
    end.

template_module(Path) ->
    Norm = re:replace(Path, "\\\\", "/", [global, {return, list}]),
    Rel  = case re:split(Norm, "priv/templates/", [{return, list}, {parts, 2}]) of
               [_, After] -> After;
               _          -> filename:basename(Path)
           end,
    Base = filename:rootname(Rel),
    Flat = re:replace(Base, "/", "_", [global, {return, list}]),
    list_to_atom(Flat ++ "_dtl").

template_dir() ->
    filename:join(code:priv_dir(test_app), "templates").

load_from_disk(Mod, OutDir) ->
    BeamFile = filename:join(OutDir, atom_to_list(Mod)),
    code:soft_purge(Mod),
    case code:load_abs(BeamFile) of
        {module, Mod} ->
            error_logger:info_msg("[templates] Loaded: ~p~n", [Mod]),
            ok;
        {error, Reason} ->
            error_logger:error_msg("[templates] load_abs failed ~p: ~p~n",
                                   [Mod, Reason]),
            {error, Reason}
    end.
