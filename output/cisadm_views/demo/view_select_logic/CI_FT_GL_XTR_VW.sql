-- SELECT logic for CISADM.CI_FT_GL_XTR_VW
SELECT
                FT.FT_ID, FT.GL_DISTRIB_STATUS
	FROM CI_FT   FT
                WHERE
                 FT.GL_DISTRIB_STATUS IN
                                ( 'M' , 'G' )
                 AND
		NOT EXISTS
		(SELECT 'X' FROM CI_FT_GL GL
			WHERE GL.FT_ID = FT.FT_ID
			        AND GL.GL_ACCT = ' ')
	AND
		EXISTS
		(SELECT 'X' FROM CI_FT_GL GL
			WHERE GL.FT_ID = FT.FT_ID
			        AND GL.GL_ACCT <> ' ')
 
