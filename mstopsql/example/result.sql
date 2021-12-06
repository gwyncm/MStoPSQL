create or replace function msload ()
returns void as $main$ begin

-- 1 ]
alter database MyData 
-- 2 ]
set owner to postgres; null ; 
-- 3 ]
alter table Customer_lookup 
-- 4 ]

-- 5 ]
add PRIMARY KEY 
-- 6 ]

-- 7 ]
( PKey ) 
-- 8 ]
; 
-- 9 ]
null ; 
-- 10 ]

-- 11 ]
set transform_null_equals = 1 
-- 12 ]
; set transform_null_equals = 1 
-- 13 ]
; null ; 
-- 14 ]

-- 15 ]
CREATE FUNCTION UDF_GetCustomers 
-- 16 ]

-- 17 ]

-- 18 ]
(
)
returns void as $$
begin

-- 19 ]
begin  DECLARE _Total int 
-- 20 ]
; begin SELECT MaxCustomers into  _Total FROM CustomerList 
-- 21 ]
limit 1 ; ; ; set escape_string_warning = 1 
-- 22 ]
; RETURN ( _Total ) 
-- 23 ]
; END 
-- 24 ]


end; $main$ language plpgsql;
