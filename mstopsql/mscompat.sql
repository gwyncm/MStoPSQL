-- This file Makes necessary changes and adds functions for MSSQL compatability.

-- Allow cast from int to bool

update pg_cast set castcontext = 'a' where castsource = 'int'::regtype 
and casttarget = 'bool'::regtype ;

-- Load plpgsql for functions

create language plpgsql;

-- casting int as bytea

create or replace function  bytea(int) returns bytea as $$ 
begin return cast ($1 as bytea); end; $$ language plpgsql;

drop cast if exists (int as bytea); 
create cast (int as bytea) with function bytea(int) as implicit;

-- system catalog creation - may be instalation specific

drop sequence if exists syssequence;
create sequence syssequence start 10;

drop table if exists sysobjects;
create table sysobjects (
id int,
xtype char(2),
type char(2),
name char(20)
);

insert into sysobjects values ( 1, 'FN', 'V');
insert into sysobjects values ( 1, 'D',  'P');
insert into sysobjects values ( 1, 'u',  'PC');
insert into sysobjects values ( 1, 'u',  'FN');

drop view if exists sysindexes;
create view sysindexes (name) as select relname from pg_class;

drop view if exists sysdatabases;
create view sysdatabases (name,filename) as select datname, 'None' from pg_database;

-- object id and syscat functions

create or replace function object_id (obj  varchar(200) ) returns int as $$ begin 
declare objname varchar(200); begin
objname := lower(obj); objname := trim(both ' ' from objname);
if exists (select * from pg_class where relname = objname) then return 1; end if; 
if exists (select * from pg_trigger where tgname = objname) then return 1; end if; 
if exists (select * from pg_proc where proname = objname) then return 1; end if; 
return null; end; end; $$ language plpgsql ;

create or replace function identity(i1 int, i2 int) returns int as $$
begin return nextval('syssequence'); end; $$ language plpgsql ;

create or replace function objectproperty (id int,obj varchar(100) ) returns int as 
$$ begin return 1; end; $$ language plpgsql ;

-- operator functions

create or replace function  safediv(float,float) returns float as $$ 
begin if $2 != 0 then return $1 / $2; else return 0; end if; end; 
$$ language plpgsql;

drop operator if exists ? ( float , float );

create operator ? ( leftarg = float, rightarg = float,
procedure = safediv, commutator = ? );

create or replace function  safediv(bigint,bigint) returns bigint as $$ 
begin if $2 != 0 then return $1 / $2; else return 0; end if; end; 
$$ language plpgsql;

drop operator if exists ? ( bigint , bigint );

create operator ? ( leftarg = bigint, rightarg = bigint,
procedure = safediv, commutator = ? );

create or replace function boolcomp(b1 bool, i1 int)
returns bool as $$ begin return b1 = cast(i1 as bool); end; $$ language plpgsql;

drop operator if exists = ( bool , int );

create operator = ( leftarg = boolean, rightarg = integer,
procedure = boolcomp, commutator = = );

create or replace function concat(str1 varchar, str2 varchar)
returns varchar as $$ begin return str1 || str2; end; $$ language plpgsql;

drop operator if exists + ( varchar , varchar );

create operator + ( leftarg = varchar, rightarg = varchar,
procedure = concat, commutator = + );

-- sp_rename functions

create or replace function sp_rename(x varchar, y varchar) returns void as $$
begin execute ' alter table ' || x || ' rename to ' || y ; end; $$ language plpgsql;

create or replace function sp_rename(x varchar, y varchar, z varchar) returns void as $$
declare tab text ;
declare col text;
begin 
tab = substring(x from '^[^.]*');
col = substring(x from '[^.]*$');
execute ' alter table ' || tab || ' rename column  ' || col || ' to ' || y  ; 
end; $$ language plpgsql ;

-- date functions

create or replace function dateadd(x1 char, i2 bigint, t1 timestamp) 
returns timestamp as $$
declare iv varchar(20);
begin iv  := to_char(i2 , text) || ' ' || ix; 
return t1 + cast(iv as interval); end; $$ language plpgsql ;

create or replace function datepart(x char, i2 interval) returns int as $$
begin return date_part(x,i2); end; $$ language plpgsql ;

create or replace function getdate () returns timestamp as $$
begin return current_timestamp; end; $$ language plpgsql ;

-- isnull family

create or replace function isnull (invalue int,rvalue int) returns int as $$ begin if 
invalue is null then return rvalue; else return invalue; end if; end; $$ language plpgsql;

create or replace function isnull (invalue uuid,rvalue uuid) returns uuid as $$ begin if 
invalue is null then return rvalue; else return invalue; end if; end; $$ language plpgsql;

create or replace function isnull (invalue bit,rvalue bit) returns bit as $$ begin if 
invalue is null then return rvalue; else return invalue; end if; end; $$ language plpgsql;

create or replace function isnull (invalue varchar,rvalue varchar) returns varchar as $$ 
begin if invalue is null then return rvalue; else return invalue; end if; 
end; $$ language plpgsql;

-- various other functions

create or replace function newid () returns uuid as $$
begin return uuid_generate_v4(); end; $$ language plpgsql ;

create or replace function sp_executesql () returns int as $$
begin return 0; end; $$ language plpgsql ;


