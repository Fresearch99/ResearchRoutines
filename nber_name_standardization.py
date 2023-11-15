"""
DATE: 11/14/2023
AUTHOR: Dominik Jurek
METHOD: Translation of the NBER patent project name standardization routine Python
        Reference: https://sites.google.com/site/patentdataproject/Home/posts/namestandardizationroutinesuploaded
        
        The NBER patent project used stata routines to standardize the 
        names of firms in Compustat and patent data for record matching.
        The name standardization routine is widely used to match firms via names.
        
        
USE:    Clean_names is the main function, taking as first argument the company name
        in string format.  Three boolean argument follow, which are by default set to
        false: 

        Arg for Clean_names:
            name -> string of company name 
            corporate_id_bool=False -> bool if a bool should be returned as third output that
                                        is True for firm identifiers in the 'name'
            adjusted=False -> bool if additional adjusted name cleaning should be performed
            uspto_add_cleaning=False -> bool if name cleaning specific for USPTO assignees should
                                        be performed
        
        Output:
            if corporate_id_bool=False:
                tuple with two values:
                standard_name -> cleaned name
                stemmed_name -> cleaned name with corporate identifiers removed
            if corporate_id_bool=True:
                tuple with above two values and third value that is True if the name matches 
                    an the string structure of a corporate name 
"""
import re

# Files not used:
#  corpentities.do => makes list of unique corporate entities with many by hand matchings
#  non_corporates.do => attempts to identify non-corporates by looking for words such as "UNIVERSITY"
# main_coname2.do: Same as main cleaning trimmed for USPTO assingees
#   (I include a dummy allowing for a similar outcome in cleaning when needed)

# %%
###############################################
# Procedure 1 Remove punctuation              #
###############################################

def punctuation(standard_name, uspto_add_cleaning):
    # =============================================================================
    # ****************************************************************
    # ** Procedure 1 Remove punctuation and standardise some symbols
    # **
    # ** modified by BHH August 2006 to change var name and remove some
    # ** initializations and arguments
    # * modified JB 1/2007 turn off Y and E for all file types
    # ****************************************************************
    # =============================================================================

    # Onw constribution, first stip leading and trailing white space and translate to lower
    # Then add white space around string to match description
    standard_name = ' '+standard_name.upper().strip()+' '

    #cap prog drop punctuation
    #prog def punctuation

    #** British - specific problem with names that end in (THE) and names that start with
    #** THE, so remove these

    # Acount for space padding at end!!
    standard_name = standard_name[:len(standard_name)-6] if (standard_name[len(standard_name)-6:len(standard_name)]=="(THE) ") else standard_name
    standard_name = standard_name[:len(standard_name)-5] if (standard_name[len(standard_name)-5:len(standard_name)]=="(THE)") else standard_name

    standard_name = standard_name[:len(standard_name)-5] if (standard_name[len(standard_name)-5:len(standard_name)]=="-OLD ") else standard_name


    standard_name = standard_name[5:] if (standard_name[0:5]==" THE ") else standard_name
    standard_name = ' '+standard_name[4:] if (standard_name[0:4]=="THE ") else standard_name
    #replace standard_name=substr(standard_name, 1, len-5) if substr(standard_name, -5, 5)=="(THE)"
    #replace standard_name=substr(standard_name, 5, .) if substr(standard_name, 1, 4)=="THE "

    # =============================================================================
    # ** Replace accented characters with non-accented equivalents ****
    # # => ignore this since this should be solvable using utf-8 standard
    # potential issues with non-ascii characters might still need resolution
    # =============================================================================

    
    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------
    if uspto_add_cleaning:
        #----------------------------------------------
        # Additional Cleaning from Pian Shu:
   
        # =============================================================================
        # Remove HTML like tags   
        # =============================================================================
        for c in ["</PDAT", "<PDAT", "<HIL", 
                  "</HIL", "<SB", "</SB", 
                  "<BOLD", "</BOLD", "<SP", 
                  "</SP", "<ULINE", "</ULINE", 
                  "</STEXT", "</ONM", "</NAM", 
                  "</HI", "<"]:
            if c in standard_name:
                standard_name = standard_name.replace(c,  "", 30)
    
        # =============================================================================
        # Remove encoding characters
        # =============================================================================
        standard_name = standard_name.replace("&TIMES;", "X", 30)
        standard_name = standard_name.replace("&COMMAT;", "@", 30)   
        standard_name = standard_name.replace("&MDASH;", "-", 30)   
        
        standard_name = standard_name.replace("&RDQU ", " ", 30)   
        standard_name = standard_name.replace("&BULL;", " ", 30)   
        standard_name = standard_name.replace("&NUM;", "#", 30)   
        
        standard_name = standard_name.replace("&OCIRC ;", "O", 30)   
        standard_name = standard_name.replace("&DGR;", "O", 30)   
        standard_name = standard_name.replace("&ANGST;", "A", 30)   
        standard_name = standard_name.replace("&AELIG;", "AE", 30)   
        standard_name = standard_name.replace("&ARING;", "A", 30)   
        standard_name = standard_name.replace("&CCEDIL;", "C", 30)   
     
        for c in ["EXCL", "EQUALS", "PRIME", 
                   "STAR", "QUEST", "REG", 
                   "TRADE", "TILDE", "LDQUO",
                   "RDQUO", "LSQUO", "RSQUO", 
                   "LSQB", "RSQB", "LT", "GT"]:
            if "&"+c+";" in standard_name:
                standard_name = standard_name.replace("&"+c+";",  "", 30)
         
        for c in ["STARF", "MIDDOT", "CIRCLESOLID", "PLUSMN", "MINUS", "THGR"]:
            if "&"+c+";" in standard_name:
                standard_name = standard_name.replace("&"+c+";",  " ", 30)
    
        for c1 in ["A", "E", "I", "O", "U", "S", "N", "C", "R", "Y"]:
            for c2 in ["GRAVE", "UML", "ACUTE", "CIRC", "TILDE", "SLASH"]:
                if "&"+c1+c2+";" in standard_name:
                    standard_name = standard_name.replace("&"+c1+c2+";",  c1, 30)
    
        
        # =============================================================================
        #  deal with {}
        # =============================================================================
        for c in ["{UMLAUT OVER (", "{UMLAUT OVER", "{ACUTE OVER (", "{ACUTE OVER", 
                  "{OVERSCORE (", "{OVERSCORE", "{DOT OVER (", "{DOT OVER", 
                  "{GRAVE OVER (", "{GRAVE OVER", "{TILDE OVER (", "{TILDE OVER", 
                  "{HACEK OVER (", "{HACEK OVER", "))}", "{HAECK OVER (", "{CIRCUMFLEX OVER (", 
                  ")}", "}"]:
            if c in standard_name:
                standard_name = standard_name.replace(c,  "", 30)
                    
    
        #** This section strips out all punctuation characters
        #** and replaces them with nulls
        # Update with additional characters from Pian Shu BUT remove brackets since are cleaned separately
    
        standard_name = standard_name.replace(";"," ; ") # from old NBER routine
        # =============================================================================
        # Remove punctuation characters
        # =============================================================================
            
        for c in ["'", ";", "^", "<", ".", "`", "_", ">", "''",
                  "!", "?", "�", "{", "\\", "$",
                  "}", "|", ",", "%", "[", "�", "*", "]", "/",
                  "@", ":", "~", "#", "-",
                  "β", "–", "‘", "’", "“", "″", "”", "•", "′", "“", 
                  "”","′","″","※","™", "★", "=", "¶",
                  "„", "£"
                  #, "+", ")", "("
                  ]:
            if c in standard_name:
                standard_name = standard_name.replace(c,  "", 30)
        
        # =============================================================================
        # deal with () - remove content within
        # =============================================================================
        for c in ["(SOUTH AFRICA)", "(PROPRIETARY)", "(S)", "(SA)", "(SM)", "(UK)", "(US)",
                  "(PTY)", "(AFRICA)", "(ICS)", "(1989)", "(TS-A)", "(ISRAEL)",
                  "(ARO) (VOLCANI CENTER)", "(NIH)",
                  "(DIENST LANDBOUWKUNDIG ONDERZOEK (DLO)",
                  "(WOLVERHAMPTION) (LIMITED)",
                  "(DIV OF GREAT PACIFIC ENTERPRISES (II))",
                  "(1996 ( LTD",
                  "((PUBL)" "(UPV EHU)", 
                  "(GMBH) (CUTEC INSTITUT)",
                  "(SHENZHEN(",
                  "(SALES) PROPRIETARY)" "(INVESTMENTS)",
                  "(IMEC) VZW)"]:
            if c in standard_name:
                standard_name = standard_name.replace(c,  "", 30)

        temp1 = standard_name.count("(")
        temp2 = standard_name.count(")")
        
        if temp1+temp2==2: standard_name = re.sub("\\(.*\\)", "", standard_name)
        if (temp1==1) & (temp2==0): standard_name = re.sub("\\(.*$", "", standard_name)
        if (temp1==0) & (temp2==1): standard_name = standard_name.replace(")",  "")

    #--------------------------------------------------------------------------
    else:
        # Include brackets to be removed, since in non-USPTO assignee cleaning, I don't need to drop brackets
        standard_name = standard_name.replace(";"," ; ") # from old NBER routine, needed in USPTO assignee cleaning for encoding character removal
        standard_name = standard_name.replace("(THE)",  "", 30)
        
        for c in ["'", ";", "^", "<", ".", "`", "_", ">", "''",
                  "!", "?", "�", "{", "\\", "$",
                  "}", "|", ",", "%", "[", "�", "*", "]", "/",
                  "@", ":", "~", "#", "-",
                  "β", "–", "‘", "’", "“", "″", "”", "•", "′", "“", 
                  "”","′","″","※","™", "★", "=", "¶",
                  "„", "£", ")", "("
                  #, "+"
                  ]:
            if c in standard_name:
                standard_name = standard_name.replace(c,  "", 30)
        
    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------
    

    # =============================================================================
    # Adjust & signs
    # =============================================================================

    #** EPO Espace specific character format problems
    #** For files downloaded from EPO Espace & appears as &amp;
    #** Also recode all common words for "AND" to &

    for c in ["&AMP;", "&PLUS;", "+", " AND ", " ET ", " & AND ", " & ET ", " UND "]:
        if c in standard_name:
            standard_name = standard_name.replace(c, " & ", 5)

    standard_name = standard_name.replace("&", " & ", 30)     ## ?* BHH - ensure that & is separate word */

    #---------------------------------------
    # If additional plus signs are left, replace them
    if "+" in standard_name:
        standard_name = standard_name.replace("+",  "", 30)
    #---------------------------------------

    standard_name = standard_name.replace("  ", " ", 30)    ## ?* BHH -recode double space to space   */
    #standard_name = re.sub("\\s+", " ", standard_name, 30)
    
    
    return(standard_name)


# %%
#################################################
# Derwent Name standardiazation                 #
#################################################
def derwent_standard_name(standard_name):
    # =============================================================================
    # **********************************************************************************
    # ** This is practically code for code the Derwent standard. However, with these
    # ** commands the order they are executed is key and has been changed. The following
    # ** is a list of other changes:
    # ** 1) Processing for und and et removed.
    # ** 2) LIMITED -> LTD added by BHH
    # ** 3) various US changes by BHH
    # ** 4) space before and after added by BHH
    # ***********************************************************************************
    # =============================================================================

    # Onw constribution, first stip leading and trailing white space and translate to lower
    # Then add white space around string to match description
    standard_name = ' '+standard_name.upper().strip()+' '

    standard_name = standard_name.replace(" A B "," AB ", 1)
    standard_name = standard_name.replace(" A CALIFORNIA CORP "," CORP ", 1)
    standard_name = standard_name.replace(" A DELAWARE CORP "," CORP ", 1)
    standard_name = standard_name.replace(" AKTIEBOLAGET "," AB ", 1)
    standard_name = standard_name.replace(" AKTIEBOLAG "," AB ", 1)
    standard_name = standard_name.replace(" ACADEMY "," ACAD ", 1)
    standard_name = standard_name.replace(" ACTIEN GESELLSCHAFT "," AG ", 1)
    standard_name = standard_name.replace(" ACTIENGESELLSCHAFT "," AG ", 1)
    standard_name = standard_name.replace(" AKTIEN GESELLSCHAFT "," AG ", 1)
    standard_name = standard_name.replace(" AKTIENGESELLSCHAFT "," AG ", 1)
    standard_name = standard_name.replace(" AGRICOLAS "," AGRIC ", 1)
    standard_name = standard_name.replace(" AGRICOLA "," AGRIC ", 1)
    standard_name = standard_name.replace(" AGRICOLES "," AGRIC ", 1)
    standard_name = standard_name.replace(" AGRICOLE "," AGRIC ", 1)
    standard_name = standard_name.replace(" AGRICOLI "," AGRIC ", 1)
    standard_name = standard_name.replace(" AGRICOLTURE "," AGRIC ", 1)
    standard_name = standard_name.replace(" AGRICULTURA "," AGRIC ", 1)
    standard_name = standard_name.replace(" AGRICULTURAL "," AGRIC ", 1)
    standard_name = standard_name.replace(" AGRICULTURE "," AGRIC ", 1)
    standard_name = standard_name.replace(" AKADEMIA "," AKAD ", 1)
    standard_name = standard_name.replace(" AKADEMIEI "," AKAD ", 1)
    standard_name = standard_name.replace(" AKADEMIE "," AKAD ", 1)
    standard_name = standard_name.replace(" AKADEMII "," AKAD ", 1)
    standard_name = standard_name.replace(" AKADEMIJA "," AKAD ", 1)
    standard_name = standard_name.replace(" AKADEMIYA "," AKAD ", 1)
    standard_name = standard_name.replace(" AKADEMIYAKH "," AKAD ", 1)
    standard_name = standard_name.replace(" AKADEMIYAM "," AKAD ", 1)
    standard_name = standard_name.replace(" AKADEMIYAMI "," AKAD ", 1)
    standard_name = standard_name.replace(" AKADEMIYU "," AKAD ", 1)
    standard_name = standard_name.replace(" AKADEMI "," AKAD ", 1)
    standard_name = standard_name.replace(" ALLGEMEINER "," ALLG ", 1)
    standard_name = standard_name.replace(" ALLGEMEINE "," ALLG ", 1)
    standard_name = standard_name.replace(" ANTREPRIZA "," ANTR ", 1)
    standard_name = standard_name.replace(" APARARII "," APAR ", 1)
    standard_name = standard_name.replace(" APARATELOR "," APAR ", 1)
    standard_name = standard_name.replace(" APPARATEBAU "," APP ", 1)
    standard_name = standard_name.replace(" APPARATUS "," APP ", 1)
    standard_name = standard_name.replace(" APPARECHHI "," APP ", 1)
    standard_name = standard_name.replace(" APPAREILLAGES "," APP ", 1)
    standard_name = standard_name.replace(" APPAREILLAGE "," APP ", 1)
    standard_name = standard_name.replace(" APPAREILS "," APP ", 1)
    standard_name = standard_name.replace(" APPAREIL "," APP ", 1)
    standard_name = standard_name.replace(" APARATE "," APAR ", 1)
    standard_name = standard_name.replace(" APPARATE "," APP ", 1)
    standard_name = standard_name.replace(" APPLICATIONS "," APPL ", 1)
    standard_name = standard_name.replace(" APPLICATION "," APPL ", 1)
    standard_name = standard_name.replace(" APPLICAZIONE "," APPL ", 1)
    standard_name = standard_name.replace(" APPLICAZIONI "," APPL ", 1)
    standard_name = standard_name.replace(" ANPARTSSELSKABET "," APS ", 1)
    standard_name = standard_name.replace(" ANPARTSSELSKAB "," APS ", 1)
    standard_name = standard_name.replace(" A/S "," AS ", 1)
    standard_name = standard_name.replace(" AKTIESELSKABET "," AS ", 1)
    standard_name = standard_name.replace(" AKTIESELSKAB "," AS ", 1)
    standard_name = standard_name.replace(" ASSOCIACAO "," ASSOC ", 1)
    standard_name = standard_name.replace(" ASSOCIATED "," ASSOC ", 1)
    standard_name = standard_name.replace(" ASSOCIATES "," ASSOCIATES ", 1)
    standard_name = standard_name.replace(" ASSOCIATE "," ASSOCIATES ", 1)
    standard_name = standard_name.replace(" ASSOCIATION "," ASSOC ", 1)
    standard_name = standard_name.replace(" BETEILIGUNGSGESELLSCHAFT MBH "," BET GMBH ", 1)
    standard_name = standard_name.replace(" BETEILIGUNGS GESELLSCHAFT MIT "," BET GMBH ", 1)
    standard_name = standard_name.replace(" BETEILIGUNGSGESELLSCHAFT "," BET GES ", 1)
    standard_name = standard_name.replace(" BESCHRANKTER HAFTUNG "," BET GMBH ", 1)
    standard_name = standard_name.replace(" BROEDERNA "," BRDR ", 1)
    standard_name = standard_name.replace(" BROEDRENE "," BRDR ", 1)
    standard_name = standard_name.replace(" BRODERNA "," BRDR ", 1)
    standard_name = standard_name.replace(" BRODRENE "," BRDR ", 1)
    standard_name = standard_name.replace(" BROTHERS "," BROS ", 1)
    standard_name = standard_name.replace(" BESLOTEN VENNOOTSCHAP MET "," BV ", 1)
    standard_name = standard_name.replace(" BESLOTEN VENNOOTSCHAP "," BV ", 1)
    standard_name = standard_name.replace(" BEPERKTE AANSPRAKELIJKHEID "," BV ", 1)
    standard_name = standard_name.replace(" CLOSE CORPORATION "," CC ", 1)
    standard_name = standard_name.replace(" CENTER "," CENT ", 1)
    standard_name = standard_name.replace(" CENTRAAL "," CENT ", 1)
    standard_name = standard_name.replace(" CENTRALA "," CENT ", 1)
    standard_name = standard_name.replace(" CENTRALES "," CENT ", 1)
    standard_name = standard_name.replace(" CENTRALE "," CENT ", 1)
    standard_name = standard_name.replace(" CENTRAL "," CENT ", 1)
    standard_name = standard_name.replace(" CENTRAUX "," CENT ", 1)
    standard_name = standard_name.replace(" CENTRE "," CENT ", 1)
    standard_name = standard_name.replace(" CENTRO "," CENT ", 1)
    standard_name = standard_name.replace(" CENTRUL "," CENT ", 1)
    standard_name = standard_name.replace(" CENTRUM "," CENT ", 1)
    standard_name = standard_name.replace(" CERCETARE "," CERC ", 1)
    standard_name = standard_name.replace(" CERCETARI "," CERC ", 1)
    standard_name = standard_name.replace(" CHEMICALS "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMICAL "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMICKEJ "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMICKE "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMICKYCH "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMICKY "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMICZNE "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMICZNY "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMIE "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMII "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMISCHE "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMISCH "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMISKEJ "," CHEM ", 1)
    standard_name = standard_name.replace(" CHEMISTRY "," CHEM ", 1)
    standard_name = standard_name.replace(" CHIMICA "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMICE "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMICI "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMICO "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIC "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIEI "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIE "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIESKOJ "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMII "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIKO "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIQUES "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIQUE "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIYAKH "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIYAMI "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIYAM "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIYA "," CHIM ", 1)
    standard_name = standard_name.replace(" CHIMIYU "," CHIM ", 1)
    standard_name = standard_name.replace(" COMPAGNIE FRANCAISE "," CIE FR ", 1)
    standard_name = standard_name.replace(" COMPAGNIE GENERALE "," CIE GEN ", 1)
    standard_name = standard_name.replace(" COMPAGNIE INDUSTRIALE "," CIE IND ", 1)
    standard_name = standard_name.replace(" COMPAGNIE INDUSTRIELLE "," CIE IND ", 1)
    standard_name = standard_name.replace(" COMPAGNIE INDUSTRIELLES "," CIE IND ", 1)
    standard_name = standard_name.replace(" COMPAGNIE INTERNATIONALE "," CIE INT ", 1)
    standard_name = standard_name.replace(" COMPAGNIE NATIONALE "," CIE NAT ", 1)
    standard_name = standard_name.replace(" COMPAGNIE PARISIENNE "," CIE PARIS ", 1)
    standard_name = standard_name.replace(" COMPAGNIE PARISIENN "," CIE PARIS ", 1)
    standard_name = standard_name.replace(" COMPAGNIE PARISIEN "," CIE PARIS ", 1)
    standard_name = standard_name.replace(" COMPANIES "," CO ", 1)
    standard_name = standard_name.replace(" COMPAGNIA "," CIA ", 1)
    standard_name = standard_name.replace(" COMPANHIA "," CIA ", 1)
    standard_name = standard_name.replace(" COMPAGNIE "," CIE ", 1)
    standard_name = standard_name.replace(" COMPANY "," CO ", 1)
    standard_name = standard_name.replace(" COMBINATUL "," COMB ", 1)
    standard_name = standard_name.replace(" COMMERCIALE "," COMML ", 1)
    standard_name = standard_name.replace(" COMMERCIAL "," COMML ", 1)
    standard_name = standard_name.replace(" CONSOLIDATED "," CONSOL ", 1)
    standard_name = standard_name.replace(" CONSTRUCCIONES "," CONSTR ", 1)
    standard_name = standard_name.replace(" CONSTRUCCIONE "," CONSTR ", 1)
    standard_name = standard_name.replace(" CONSTRUCCION "," CONSTR ", 1)
    standard_name = standard_name.replace(" CONSTRUCTIE "," CONSTR ", 1)
    standard_name = standard_name.replace(" CONSTRUCTII "," CONSTR ", 1)
    standard_name = standard_name.replace(" CONSTRUCTIILOR "," CONSTR ", 1)
    standard_name = standard_name.replace(" CONSTRUCTIONS "," CONSTR ", 1)
    standard_name = standard_name.replace(" CONSTRUCTION "," CONSTR ", 1)
    standard_name = standard_name.replace(" CONSTRUCTORTUL "," CONSTR ", 1)
    standard_name = standard_name.replace(" CONSTRUCTORUL "," CONSTR ", 1)
    standard_name = standard_name.replace(" CONSTRUCTOR "," CONSTR ", 1)
    standard_name = standard_name.replace(" CO OPERATIVES "," COOP ", 1)
    standard_name = standard_name.replace(" CO OPERATIVE "," COOP ", 1)
    standard_name = standard_name.replace(" COOPERATIEVE "," COOP ", 1)
    standard_name = standard_name.replace(" COOPERATIVA "," COOP ", 1)
    standard_name = standard_name.replace(" COOPERATIVES "," COOP ", 1)
    standard_name = standard_name.replace(" COOPERATIVE "," COOP ", 1)
    standard_name = standard_name.replace(" INCORPORATED "," INC ", 1)
    standard_name = standard_name.replace(" INCORPORATION "," INC ", 1)
    standard_name = standard_name.replace(" CORPORATE "," CORP ", 1)
    standard_name = standard_name.replace(" CORPORATION OF AMERICA "," CORP ", 1)
    standard_name = standard_name.replace(" CORPORATION "," CORP ", 1)
    standard_name = standard_name.replace(" CORPORASTION "," CORP ", 1)
    standard_name = standard_name.replace(" CORPORATIOON "," CORP ", 1)
    standard_name = standard_name.replace(" COSTRUZIONI "," COSTR ", 1)
    standard_name = standard_name.replace(" DEUTSCHEN "," DDR ", 1)
    standard_name = standard_name.replace(" DEUTSCHE "," DDR ", 1)
    standard_name = standard_name.replace(" DEMOKRATISCHEN REPUBLIK "," DDR ", 1)
    standard_name = standard_name.replace(" DEMOKRATISCHE REPUBLIK "," DDR ", 1)
    standard_name = standard_name.replace(" DEPARTEMENT "," DEPT ", 1)
    standard_name = standard_name.replace(" DEPARTMENT "," DEPT ", 1)
    standard_name = standard_name.replace(" DEUTSCHES "," DEUT ", 1)
    standard_name = standard_name.replace(" DEUTSCHEN "," DEUT ", 1)
    standard_name = standard_name.replace(" DEUTSCHER "," DEUT ", 1)
    standard_name = standard_name.replace(" DEUTSCHLAND "," DEUT ", 1)
    standard_name = standard_name.replace(" DEUTSCHE "," DEUT ", 1)
    standard_name = standard_name.replace(" DEUTSCH "," DEUT ", 1)
    standard_name = standard_name.replace(" DEVELOPMENTS "," DEV ", 1)
    standard_name = standard_name.replace(" DEVELOPMENT "," DEV ", 1)
    standard_name = standard_name.replace(" DEVELOPPEMENTS "," DEV ", 1)
    standard_name = standard_name.replace(" DEVELOPPEMENT "," DEV ", 1)
    standard_name = standard_name.replace(" DEVELOP "," DEV ", 1)
    standard_name = standard_name.replace(" DIVISIONE "," DIV ", 1)
    standard_name = standard_name.replace(" DIVISION "," DIV ", 1)
    standard_name = standard_name.replace(" ENGINEERING "," ENG ", 1)
    standard_name = standard_name.replace(" EQUIPEMENTS "," EQUIP ", 1)
    standard_name = standard_name.replace(" EQUIPEMENT "," EQUIP ", 1)
    standard_name = standard_name.replace(" EQUIPMENTS "," EQUIP ", 1)
    standard_name = standard_name.replace(" EQUIPMENT "," EQUIP ", 1)
    standard_name = standard_name.replace(" ESTABLISHMENTS "," ESTAB ", 1)
    standard_name = standard_name.replace(" ESTABLISHMENT "," ESTAB ", 1)
    standard_name = standard_name.replace(" ESTABLISSEMENTS "," ESTAB ", 1)
    standard_name = standard_name.replace(" ESTABLISSEMENT "," ESTAB ", 1)
    standard_name = standard_name.replace(" ETABLISSEMENTS "," ETAB ", 1)
    standard_name = standard_name.replace(" ETABLISSEMENT "," ETAB ", 1)
    standard_name = standard_name.replace(" ETABS "," ETAB ", 1)
    standard_name = standard_name.replace(" ETS "," ETAB ", 1)
    standard_name = standard_name.replace(" ETUDES "," ETUD ", 1)
    standard_name = standard_name.replace(" ETUDE "," ETUD ", 1)
    standard_name = standard_name.replace(" EUROPAEISCHEN "," EURO ", 1)
    standard_name = standard_name.replace(" EUROPAEISCHES "," EURO ", 1)
    standard_name = standard_name.replace(" EUROPAEISCHE "," EURO ", 1)
    standard_name = standard_name.replace(" EUROPAISCHEN "," EURO ", 1)
    standard_name = standard_name.replace(" EUROPAISCHES "," EURO ", 1)
    standard_name = standard_name.replace(" EUROPAISCHE "," EURO ", 1)
    standard_name = standard_name.replace(" EUROPEAN "," EURO ", 1)
    standard_name = standard_name.replace(" EUROPEENNE "," EURO ", 1)
    standard_name = standard_name.replace(" EUROPEEN "," EURO ", 1)
    standard_name = standard_name.replace(" EUROPEA "," EURO ", 1)
    standard_name = standard_name.replace(" EUROPE "," EURO ", 1)
    standard_name = standard_name.replace(" EINGETRAGENER VEREIN "," EV ", 1)
    standard_name = standard_name.replace(" EXPLOATERINGS "," EXPL ", 1)
    standard_name = standard_name.replace(" EXPLOATERING "," EXPL ", 1)
    standard_name = standard_name.replace(" EXPLOITATIE "," EXPL ", 1)
    standard_name = standard_name.replace(" EXPLOITATIONS "," EXPL ", 1)
    standard_name = standard_name.replace(" EXPLOITATION "," EXPL ", 1)
    standard_name = standard_name.replace(" FIRMA "," FA ", 1)
    standard_name = standard_name.replace(" FABBRICAZIONI "," FAB ", 1)
    standard_name = standard_name.replace(" FABBRICHE "," FAB ", 1)
    standard_name = standard_name.replace(" FABRICATIONS "," FAB ", 1)
    standard_name = standard_name.replace(" FABRICATION "," FAB ", 1)
    standard_name = standard_name.replace(" FABBRICA "," FAB ", 1)
    standard_name = standard_name.replace(" FABRICA "," FAB ", 1)
    standard_name = standard_name.replace(" FABRIEKEN "," FAB ", 1)
    standard_name = standard_name.replace(" FABRIEK "," FAB ", 1)
    standard_name = standard_name.replace(" FABRIKER "," FAB ", 1)
    standard_name = standard_name.replace(" FABRIK "," FAB ", 1)
    standard_name = standard_name.replace(" FABRIQUES "," FAB ", 1)
    standard_name = standard_name.replace(" FABRIQUE "," FAB ", 1)
    standard_name = standard_name.replace(" FABRIZIO "," FAB ", 1)
    standard_name = standard_name.replace(" FABRYKA "," FAB ", 1)
    standard_name = standard_name.replace(" FARMACEUTICA "," FARM ", 1)
    standard_name = standard_name.replace(" FARMACEUTICE "," FARM ", 1)
    standard_name = standard_name.replace(" FARMACEUTICHE "," FARM ", 1)
    standard_name = standard_name.replace(" FARMACEUTICI "," FARM ", 1)
    standard_name = standard_name.replace(" FARMACEUTICOS "," FARM ", 1)
    standard_name = standard_name.replace(" FARMACEUTICO "," FARM ", 1)
    standard_name = standard_name.replace(" FARMACEUTISK "," FARM ", 1)
    standard_name = standard_name.replace(" FARMACEVTSKIH "," FARM ", 1)
    standard_name = standard_name.replace(" FARMACIE "," FARM ", 1)
    standard_name = standard_name.replace(" FONDATION "," FOND ", 1)
    standard_name = standard_name.replace(" FONDAZIONE "," FOND ", 1)
    standard_name = standard_name.replace(" FOUNDATIONS "," FOUND ", 1)
    standard_name = standard_name.replace(" FOUNDATION "," FOUND ", 1)
    standard_name = standard_name.replace(" FRANCAISE "," FR ", 1)
    standard_name = standard_name.replace(" FRANCAIS "," FR ", 1)
    standard_name = standard_name.replace(" F LLI "," FRAT ", 1)
    standard_name = standard_name.replace(" FLLI "," FRAT ", 1)
    standard_name = standard_name.replace(" FRATELLI "," FRAT ", 1)
    standard_name = standard_name.replace(" GEBRODERS "," GEBR ", 1)
    standard_name = standard_name.replace(" GEBRODER "," GEBR ", 1)
    standard_name = standard_name.replace(" GEBROEDERS "," GEBR ", 1)
    standard_name = standard_name.replace(" GEBROEDER "," GEBR ", 1)
    standard_name = standard_name.replace(" GEBRUDERS "," GEBR ", 1)
    standard_name = standard_name.replace(" GEBRUDER "," GEBR ", 1)
    standard_name = standard_name.replace(" GEBRUEDERS "," GEBR ", 1)
    standard_name = standard_name.replace(" GEBRUEDER "," GEBR ", 1)
    standard_name = standard_name.replace(" GEB "," GEBR ", 1)
    standard_name = standard_name.replace(" GENERALA "," GEN ", 1)
    standard_name = standard_name.replace(" GENERALES "," GEN ", 1)
    standard_name = standard_name.replace(" GENERALE "," GEN ", 1)
    standard_name = standard_name.replace(" GENERAL "," GEN ", 1)
    standard_name = standard_name.replace(" GENERAUX "," GEN ", 1)
    standard_name = standard_name.replace(" GESELLSCHAFT "," GES ", 1)
    standard_name = standard_name.replace(" GEWERKSCHAFT "," GEW ", 1)
    standard_name = standard_name.replace(" GAKKO HOJIN "," GH ", 1)
    standard_name = standard_name.replace(" GAKKO HOUJIN "," GH ", 1)
    standard_name = standard_name.replace(" GUTEHOFFNUNGSCHUETTE "," GHH ", 1)
    standard_name = standard_name.replace(" GUTEHOFFNUNGSCHUTTE "," GHH ", 1)
    standard_name = standard_name.replace(" GOMEI GAISHA "," GK ", 1)
    standard_name = standard_name.replace(" GOMEI KAISHA "," GK ", 1)
    standard_name = standard_name.replace(" GOSHI KAISHA "," GK ", 1)
    standard_name = standard_name.replace(" GOUSHI GAISHA "," GK ", 1)
    standard_name = standard_name.replace(" GESELLSCHAFT MBH "," GMBH ", 1)
    standard_name = standard_name.replace(" GESELLSCHAFT MIT BESCHRANKTER HAFTUNG "," GMBH ", 1)
    standard_name = standard_name.replace(" GROUPEMENT "," GRP ", 1)
    standard_name = standard_name.replace(" GROUPMENT "," GRP ", 1)
    standard_name = standard_name.replace(" HANDELSMAATSCHAPPIJ "," HANDL ", 1)
    standard_name = standard_name.replace(" HANDELSMIJ "," HANDL ", 1)
    standard_name = standard_name.replace(" HANDELS BOLAGET "," HB ", 1)
    standard_name = standard_name.replace(" HANDELSBOLAGET "," HB ", 1)
    standard_name = standard_name.replace(" HER MAJESTY THE QUEEN IN RIGHT OF CANADA AS REPRESENTED BY THE MINISTER OF "," CANADA MIN OF ", 1)
    standard_name = standard_name.replace(" HER MAJESTY THE QUEEN "," UK ", 1)
    standard_name = standard_name.replace(" INDUSTRIAS "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIALS "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIAL "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIALA "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIALE "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIALIZARE "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIALIZAREA "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIALI "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIEELE "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIEI "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIELS "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIELLES "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIELLE "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIELL "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIEL "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIER "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIES "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRII "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIJ "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIYAKH "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIYAM "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIYAMI "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIYA "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIYU "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIA "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRIE "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRI "," IND ", 1)
    standard_name = standard_name.replace(" INDUSTRY "," IND ", 1)
    standard_name = standard_name.replace(" INGENIERIA "," ING ", 1)
    standard_name = standard_name.replace(" INGENIER "," ING ", 1)
    standard_name = standard_name.replace(" INGENIEURS "," ING ", 1)
    standard_name = standard_name.replace(" INGENIEURBUERO "," ING ", 1)
    standard_name = standard_name.replace(" INGENIEURBUREAU "," ING ", 1)
    standard_name = standard_name.replace(" INGENIEURBURO "," ING ", 1)
    standard_name = standard_name.replace(" INGENIEURGESELLSCHAFT "," ING ", 1)
    standard_name = standard_name.replace(" INGENIEURSBUREAU "," ING ", 1)
    standard_name = standard_name.replace(" INGENIEURTECHNISCHES "," ING ", 1)
    standard_name = standard_name.replace(" INGENIEURTECHNISCHE "," ING ", 1)
    standard_name = standard_name.replace(" INGENIEUR "," ING ", 1)
    standard_name = standard_name.replace(" INGENIOERFIRMAET "," ING ", 1)
    standard_name = standard_name.replace(" INGENIORSFIRMAN "," ING ", 1)
    standard_name = standard_name.replace(" INGENIORSFIRMA "," ING ", 1)
    standard_name = standard_name.replace(" INGENJORSFIRMA "," ING ", 1)
    standard_name = standard_name.replace(" INGINERIE "," ING ", 1)
    standard_name = standard_name.replace(" INSTITUTE FRANCAISE "," INST FR ", 1)
    standard_name = standard_name.replace(" INSTITUT FRANCAIS "," INST FR ", 1)
    standard_name = standard_name.replace(" INSTITUTE NATIONALE "," INST NAT ", 1)
    standard_name = standard_name.replace(" INSTITUT NATIONAL "," INST NAT ", 1)
    standard_name = standard_name.replace(" INSTITUTAMI "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTAMKH "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTAM "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTA "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTES "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTET "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTE "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTOM "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTOV "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTO "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTT "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTUL "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTU "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUTY "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUT "," INST ", 1)
    standard_name = standard_name.replace(" INSTITUUT "," INST ", 1)
    standard_name = standard_name.replace(" INSTITZHT "," INST ", 1)
    standard_name = standard_name.replace(" INSTYTUT "," INST ", 1)
    standard_name = standard_name.replace(" INSINOORITOMISTO "," INSTMSTO ", 1)
    standard_name = standard_name.replace(" INSTRUMENTS "," INSTR ", 1)
    standard_name = standard_name.replace(" INSTRUMENTATION "," INSTR ", 1)
    standard_name = standard_name.replace(" INSTRUMENTE "," INSTR ", 1)
    standard_name = standard_name.replace(" INSTRUMENT "," INSTR ", 1)
    standard_name = standard_name.replace(" INTERNATL "," INT ", 1)
    standard_name = standard_name.replace(" INTERNACIONAL "," INT ", 1)
    standard_name = standard_name.replace(" INTERNATIONAL "," INT ", 1)
    standard_name = standard_name.replace(" INTERNATIONALEN "," INT ", 1)
    standard_name = standard_name.replace(" INTERNATIONALE "," INT ", 1)
    standard_name = standard_name.replace(" INTERNATIONAUX "," INT ", 1)
    standard_name = standard_name.replace(" INTERNATIONELLA "," INT ", 1)
    standard_name = standard_name.replace(" INTERNAZIONALE "," INT ", 1)
    standard_name = standard_name.replace(" INTL "," INT ", 1)
    standard_name = standard_name.replace(" INTREPRINDEREA "," INTR ", 1)
    standard_name = standard_name.replace(" ISTITUTO "," IST ", 1)
    standard_name = standard_name.replace(" ITALIANA "," ITAL ", 1)
    standard_name = standard_name.replace(" ITALIANE "," ITAL ", 1)
    standard_name = standard_name.replace(" ITALIANI "," ITAL ", 1)
    standard_name = standard_name.replace(" ITALIANO "," ITAL ", 1)
    standard_name = standard_name.replace(" ITALIENNE "," ITAL ", 1)
    standard_name = standard_name.replace(" ITALIEN "," ITAL ", 1)
    standard_name = standard_name.replace(" ITALIAN "," ITAL ", 1)
    standard_name = standard_name.replace(" ITALIA "," ITAL ", 1)
    standard_name = standard_name.replace(" ITALI "," ITAL ", 1)
    standard_name = standard_name.replace(" ITALO "," ITAL ", 1)
    standard_name = standard_name.replace(" ITALY "," ITAL ", 1)
    standard_name = standard_name.replace(" JUNIOR "," JR ", 1)
    standard_name = standard_name.replace(" KOMMANDIT BOLAG "," KB ", 1)
    standard_name = standard_name.replace(" KOMMANDIT BOLAGET "," KB ", 1)
    standard_name = standard_name.replace(" KOMMANDITBOLAGET "," KB ", 1)
    standard_name = standard_name.replace(" KOMMANDITBOLAG "," KB ", 1)
    standard_name = standard_name.replace(" KOMMANDIT GESELLSCHAFT "," KG ", 1)
    standard_name = standard_name.replace(" KOMMANDITGESELLSCHAFT "," KG ", 1)
    standard_name = standard_name.replace(" KOMMANDIT GESELLSCHAFT AUF AKTIEN "," KGAA ", 1)
    standard_name = standard_name.replace(" KOMMANDITGESELLSCHAFT AUF AKTIEN "," KGAA ", 1)
    standard_name = standard_name.replace(" KUTATO INTEZETE "," KI ", 1)
    standard_name = standard_name.replace(" KUTATO INTEZET "," KI ", 1)
    standard_name = standard_name.replace(" KUTATOINTEZETE "," KI ", 1)
    standard_name = standard_name.replace(" KUTATOINTEZET "," KI ", 1)
    standard_name = standard_name.replace(" KABUSHIKI GAISHA "," KK ", 1)
    standard_name = standard_name.replace(" KABUSHIKI KAISHA "," KK ", 1)
    standard_name = standard_name.replace(" KABUSHIKI GAISYA "," KK ", 1)
    standard_name = standard_name.replace(" KABUSHIKI KAISYA "," KK ", 1)
    standard_name = standard_name.replace(" KABUSHIKIGAISHA "," KK ", 1)
    standard_name = standard_name.replace(" KABUSHIKIKAISHA "," KK ", 1)
    standard_name = standard_name.replace(" KABUSHIKIGAISYA "," KK ", 1)
    standard_name = standard_name.replace(" KABUSHIKIKAISYA "," KK ", 1)
    standard_name = standard_name.replace(" KOMBINATU "," KOMB ", 1)
    standard_name = standard_name.replace(" KOMBINATY "," KOMB ", 1)
    standard_name = standard_name.replace(" KOMBINAT "," KOMB ", 1)
    standard_name = standard_name.replace(" KONINKLIJKE "," KONINK ", 1)
    standard_name = standard_name.replace(" KONCERNOVY PODNIK "," KP ", 1)
    standard_name = standard_name.replace(" KUNSTSTOFFTECHNIK "," KUNST ", 1)
    standard_name = standard_name.replace(" KUNSTSTOFF "," KUNST ", 1)
    standard_name = standard_name.replace(" LABORATOIRES "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATOIRE "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATOIR "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATORIEI "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATORIES "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATORII "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATORIJ "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATORIOS "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATORIO "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATORIUM "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATORI "," LAB ", 1)
    standard_name = standard_name.replace(" LABORATORY "," LAB ", 1)
    standard_name = standard_name.replace(" LABORTORI "," LAB ", 1)
    standard_name = standard_name.replace(" LAVORAZA "," LAVORAZ ", 1)
    standard_name = standard_name.replace(" LAVORAZIONE "," LAVORAZ ", 1)
    standard_name = standard_name.replace(" LAVORAZIONI "," LAVORAZ ", 1)
    standard_name = standard_name.replace(" LAVORAZIO "," LAVORAZ ", 1)
    standard_name = standard_name.replace(" LAVORAZI "," LAVORAZ ", 1)
    standard_name = standard_name.replace(" LIMITED PARTNERSHIP "," LP ", 1)
    standard_name = standard_name.replace(" LIMITED "," LTD ", 1)
    standard_name = standard_name.replace(" LTD LTEE "," LTD ", 1)
    standard_name = standard_name.replace(" MASCHINENVERTRIEB "," MASCH ", 1)
    standard_name = standard_name.replace(" MASCHINENBAUANSTALT "," MASCHBAU ", 1)
    standard_name = standard_name.replace(" MASCHINENBAU "," MASCHBAU ", 1)
    standard_name = standard_name.replace(" MASCHINENFABRIEK "," MASCHFAB ", 1)
    standard_name = standard_name.replace(" MASCHINENFABRIKEN "," MASCHFAB ", 1)
    standard_name = standard_name.replace(" MASCHINENFABRIK "," MASCHFAB ", 1)
    standard_name = standard_name.replace(" MASCHINENFAB "," MASCHFAB ", 1)
    standard_name = standard_name.replace(" MASCHINEN "," MASCH ", 1)
    standard_name = standard_name.replace(" MASCHIN "," MASCH ", 1)
    standard_name = standard_name.replace(" MIT BESCHRANKTER HAFTUNG "," MBH ", 1)
    standard_name = standard_name.replace(" MANUFACTURINGS "," MFG ", 1)
    standard_name = standard_name.replace(" MANUFACTURING "," MFG ", 1)
    standard_name = standard_name.replace(" MANIFATTURAS "," MFR ", 1)
    standard_name = standard_name.replace(" MANIFATTURA "," MFR ", 1)
    standard_name = standard_name.replace(" MANIFATTURE "," MFR ", 1)
    standard_name = standard_name.replace(" MANUFACTURAS "," MFR ", 1)
    standard_name = standard_name.replace(" MANUFACTURERS "," MFR ", 1)
    standard_name = standard_name.replace(" MANUFACTURER "," MFR ", 1)
    standard_name = standard_name.replace(" MANUFACTURES "," MFR ", 1)
    standard_name = standard_name.replace(" MANUFACTURE "," MFR ", 1)
    standard_name = standard_name.replace(" MANUFATURA "," MFR ", 1)
    standard_name = standard_name.replace(" MAATSCHAPPIJ "," MIJ ", 1)
    standard_name = standard_name.replace(" MEDICAL "," MED ", 1)
    standard_name = standard_name.replace(" MINISTERE "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERIUM "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERO "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERSTVAKH "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERSTVAM "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERSTVAMI "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERSTVA "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERSTVE "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERSTVO "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERSTVOM "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERSTVU "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERSTV "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERSTWO "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTERUL "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTRE "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTRY "," MIN ", 1)
    standard_name = standard_name.replace(" MINISTER "," MIN ", 1)
    standard_name = standard_name.replace(" MAGYAR TUDOMANYOS AKADEMIA "," MTA ", 1)
    standard_name = standard_name.replace(" NATIONAAL "," NAT ", 1)
    standard_name = standard_name.replace(" NATIONAL "," NAT ", 1)
    standard_name = standard_name.replace(" NATIONALE "," NAT ", 1)
    standard_name = standard_name.replace(" NATIONAUX "," NAT ", 1)
    standard_name = standard_name.replace(" NATL "," NAT ", 1)
    standard_name = standard_name.replace(" NAZIONALE "," NAZ ", 1)
    standard_name = standard_name.replace(" NAZIONALI "," NAZ ", 1)
    standard_name = standard_name.replace(" NORDDEUTSCH "," NORDDEUT ", 1)
    standard_name = standard_name.replace(" NORDDEUTSCHE "," NORDDEUT ", 1)
    standard_name = standard_name.replace(" NORDDEUTSCHER "," NORDDEUT ", 1)
    standard_name = standard_name.replace(" NORDDEUTSCHES "," NORDDEUT ", 1)
    standard_name = standard_name.replace(" NARODNI PODNIK "," NP ", 1)
    standard_name = standard_name.replace(" NARODNIJ PODNIK "," NP ", 1)
    standard_name = standard_name.replace(" NARODNY PODNIK "," NP ", 1)
    standard_name = standard_name.replace(" NAAMLOOSE VENOOTSCHAP "," NV ", 1)
    standard_name = standard_name.replace(" NAAMLOZE VENNOOTSCHAP "," NV ", 1)
    standard_name = standard_name.replace(" N V "," NV ", 1)
    standard_name = standard_name.replace(" OESTERREICHISCHES "," OESTERR ", 1)
    standard_name = standard_name.replace(" OESTERREICHISCHE "," OESTERR ", 1)
    standard_name = standard_name.replace(" OESTERREICHISCH "," OESTERR ", 1)
    standard_name = standard_name.replace(" OESTERREICH "," OESTERR ", 1)
    standard_name = standard_name.replace(" OSTERREICHISCHES "," OESTERR ", 1)
    standard_name = standard_name.replace(" OSTERREICHISCHE "," OESTERR ", 1)
    standard_name = standard_name.replace(" OSTERREICHISCH "," OESTERR ", 1)
    standard_name = standard_name.replace(" OSTERREICH "," OESTERR ", 1)
    standard_name = standard_name.replace(" OFFICINE MECCANICA "," OFF MEC ", 1)
    standard_name = standard_name.replace(" OFFICINE MECCANICHE "," OFF MEC ", 1)
    standard_name = standard_name.replace(" OFFICINE NATIONALE "," OFF NAT ", 1)
    standard_name = standard_name.replace(" OFFENE HANDELSGESELLSCHAFT "," OHG ", 1)
    standard_name = standard_name.replace(" ONTWIKKELINGSBUREAU "," ONTWIK ", 1)
    standard_name = standard_name.replace(" ONTWIKKELINGS "," ONTWIK ", 1)
    standard_name = standard_name.replace(" OBOROVY PODNIK "," OP ", 1)
    standard_name = standard_name.replace(" ORGANISATIE "," ORG ", 1)
    standard_name = standard_name.replace(" ORGANISATIONS "," ORG ", 1)
    standard_name = standard_name.replace(" ORGANISATION "," ORG ", 1)
    standard_name = standard_name.replace(" ORGANIZATIONS "," ORG ", 1)
    standard_name = standard_name.replace(" ORGANIZATION "," ORG ", 1)
    standard_name = standard_name.replace(" ORGANIZZAZIONE "," ORG ", 1)
    standard_name = standard_name.replace(" OSAKEYHTIO "," OY ", 1)
    standard_name = standard_name.replace(" PHARMACEUTICALS "," PHARM ", 1)
    standard_name = standard_name.replace(" PHARMACEUTICAL "," PHARM ", 1)
    standard_name = standard_name.replace(" PHARMACEUTICA "," PHARM ", 1)
    standard_name = standard_name.replace(" PHARMACEUTIQUES "," PHARM ", 1)
    standard_name = standard_name.replace(" PHARMACEUTIQUE "," PHARM ", 1)
    standard_name = standard_name.replace(" PHARMAZEUTIKA "," PHARM ", 1)
    standard_name = standard_name.replace(" PHARMAZEUTISCHEN "," PHARM ", 1)
    standard_name = standard_name.replace(" PHARMAZEUTISCHE "," PHARM ", 1)
    standard_name = standard_name.replace(" PHARMAZEUTISCH "," PHARM ", 1)
    standard_name = standard_name.replace(" PHARMAZIE "," PHARM ", 1)
    standard_name = standard_name.replace(" PUBLIC LIMITED COMPANY "," PLC ", 1)
    standard_name = standard_name.replace(" PRELUCRAREA "," PRELUC ", 1)
    standard_name = standard_name.replace(" PRELUCRARE "," PRELUC ", 1)
    standard_name = standard_name.replace(" PRODOTTI "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUCE "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUCTS "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUCT "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUCTAS "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUCTA "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUCTIE "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUCTOS "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUCTO "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUCTORES "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUITS "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUIT "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUKCJI "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUKTER "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUKTE "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUKT "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUSE "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUTOS "," PROD ", 1)
    standard_name = standard_name.replace(" PRODUIT CHIMIQUES "," PROD CHIM ", 1)
    standard_name = standard_name.replace(" PRODUIT CHIMIQUE "," PROD CHIM ", 1)
    standard_name = standard_name.replace(" PRODUCTIONS "," PRODN ", 1)
    standard_name = standard_name.replace(" PRODUCTION "," PRODN ", 1)
    standard_name = standard_name.replace(" PRODUKTIONS "," PRODN ", 1)
    standard_name = standard_name.replace(" PRODUKTION "," PRODN ", 1)
    standard_name = standard_name.replace(" PRODUZIONI "," PRODN ", 1)
    standard_name = standard_name.replace(" PROIECTARE "," PROI ", 1)
    standard_name = standard_name.replace(" PROIECTARI "," PROI ", 1)
    standard_name = standard_name.replace(" PRZEDSIEBIOSTWO "," PRZEDSIEB ", 1)
    standard_name = standard_name.replace(" PRZEMYSLU "," PRZEYM ", 1)
    standard_name = standard_name.replace(" PROPRIETARY "," PTY ", 1)
    standard_name = standard_name.replace(" PERSONENVENNOOTSCHAP MET "," PVBA ", 1)
    standard_name = standard_name.replace(" BEPERKTE AANSPRAKELIJKHEID "," PVBA ", 1)
    standard_name = standard_name.replace(" REALISATIONS "," REAL ", 1)
    standard_name = standard_name.replace(" REALISATION "," REAL ", 1)
    standard_name = standard_name.replace(" RECHERCHES "," RECH ", 1)
    standard_name = standard_name.replace(" RECHERCHE "," RECH ", 1)
    standard_name = standard_name.replace(" RECHERCHES ET DEVELOPMENTS "," RECH & DEV ", 1)
    standard_name = standard_name.replace(" RECHERCHE ET DEVELOPMENT "," RECH & DEV ", 1)
    standard_name = standard_name.replace(" RECHERCHES ET DEVELOPPEMENTS "," RECH & DEV ", 1)
    standard_name = standard_name.replace(" RECHERCHE ET DEVELOPPEMENT "," RECH & DEV ", 1)
    standard_name = standard_name.replace(" RESEARCH & DEVELOPMENT "," RES & DEV ", 1)
    standard_name = standard_name.replace(" RESEARCH AND DEVELOPMENT "," RES & DEV ", 1)
    standard_name = standard_name.replace(" RESEARCH "," RES ", 1)
    standard_name = standard_name.replace(" RIJKSUNIVERSITEIT "," RIJKSUNIV ", 1)
    standard_name = standard_name.replace(" SECRETATY "," SECRETARY ", 1)
    standard_name = standard_name.replace(" SECRETRY "," SECRETARY ", 1)
    standard_name = standard_name.replace(" SECREATRY "," SECRETARY ", 1)
    standard_name = standard_name.replace(" SOCIEDAD ANONIMA "," SA ", 1)
    standard_name = standard_name.replace(" SOCIETE ANONYME DITE "," SA ", 1)
    standard_name = standard_name.replace(" SOCIETE ANONYME "," SA ", 1)
    standard_name = standard_name.replace(" SOCIETE A RESPONSABILITE LIMITEE "," SARL ", 1)
    standard_name = standard_name.replace(" SOCIETE A RESPONSIBILITE LIMITEE "," SARL ", 1)
    standard_name = standard_name.replace(" SOCIETA IN ACCOMANDITA SEMPLICE "," SAS ", 1)
    standard_name = standard_name.replace(" SCHWEIZERISCHES "," SCHWEIZ ", 1)
    standard_name = standard_name.replace(" SCHWEIZERISCHER "," SCHWEIZ ", 1)
    standard_name = standard_name.replace(" SCHWEIZERISCHE "," SCHWEIZ ", 1)
    standard_name = standard_name.replace(" SCHWEIZERISCH "," SCHWEIZ ", 1)
    standard_name = standard_name.replace(" SCHWEIZER "," SCHWEIZ ", 1)
    standard_name = standard_name.replace(" SCIENCES "," SCI ", 1)
    standard_name = standard_name.replace(" SCIENCE "," SCI ", 1)
    standard_name = standard_name.replace(" SCIENTIFICA "," SCI ", 1)
    standard_name = standard_name.replace(" SCIENTIFIC "," SCI ", 1)
    standard_name = standard_name.replace(" SCIENTIFIQUES "," SCI ", 1)
    standard_name = standard_name.replace(" SCIENTIFIQUE "," SCI ", 1)
    standard_name = standard_name.replace(" SHADAN HOJIN "," SH ", 1)
    standard_name = standard_name.replace(" SIDERURGICAS "," SIDER ", 1)
    standard_name = standard_name.replace(" SIDERURGICA "," SIDER ", 1)
    standard_name = standard_name.replace(" SIDERURGIC "," SIDER ", 1)
    standard_name = standard_name.replace(" SIDERURGIE "," SIDER ", 1)
    standard_name = standard_name.replace(" SIDERURGIQUE "," SIDER ", 1)
    standard_name = standard_name.replace(" SOCIETA IN NOME COLLECTIVO "," SNC ", 1)
    standard_name = standard_name.replace(" SOCIETE EN NOM COLLECTIF "," SNC ", 1)
    standard_name = standard_name.replace(" SOCIETE ALSACIENNE "," SOC ALSAC ", 1)
    standard_name = standard_name.replace(" SOCIETE APPLICATION "," SOC APPL ", 1)
    standard_name = standard_name.replace(" SOCIETA APPLICAZIONE "," SOC APPL ", 1)
    standard_name = standard_name.replace(" SOCIETE AUXILIAIRE "," SOC AUX ", 1)
    standard_name = standard_name.replace(" SOCIETE CHIMIQUE "," SOC CHIM ", 1)
    standard_name = standard_name.replace(" SOCIEDAD CIVIL "," SOC CIV ", 1)
    standard_name = standard_name.replace(" SOCIETE CIVILE "," SOC CIV ", 1)
    standard_name = standard_name.replace(" SOCIETE COMMERCIALES "," SOC COMML ", 1)
    standard_name = standard_name.replace(" SOCIETE COMMERCIALE "," SOC COMML ", 1)
    standard_name = standard_name.replace(" SOCIEDAD ESPANOLA "," SOC ESPAN ", 1)
    standard_name = standard_name.replace(" SOCIETE ETUDES "," SOC ETUD ", 1)
    standard_name = standard_name.replace(" SOCIETE ETUDE "," SOC ETUD ", 1)
    standard_name = standard_name.replace(" SOCIETE EXPLOITATION "," SOC EXPL ", 1)
    standard_name = standard_name.replace(" SOCIETE GENERALE "," SOC GEN ", 1)
    standard_name = standard_name.replace(" SOCIETE INDUSTRIELLES "," SOC IND ", 1)
    standard_name = standard_name.replace(" SOCIETE INDUSTRIELLE "," SOC IND ", 1)
    standard_name = standard_name.replace(" SOCIETE MECANIQUES "," SOC MEC ", 1)
    standard_name = standard_name.replace(" SOCIETE MECANIQUE "," SOC MEC ", 1)
    standard_name = standard_name.replace(" SOCIETE NATIONALE "," SOC NAT ", 1)
    standard_name = standard_name.replace(" SOCIETE NOUVELLE "," SOC NOUV ", 1)
    standard_name = standard_name.replace(" SOCIETE PARISIENNE "," SOC PARIS ", 1)
    standard_name = standard_name.replace(" SOCIETE PARISIENN "," SOC PARIS ", 1)
    standard_name = standard_name.replace(" SOCIETE PARISIEN "," SOC PARIS ", 1)
    standard_name = standard_name.replace(" SOCIETE TECHNIQUES "," SOC TECH ", 1)
    standard_name = standard_name.replace(" SOCIETE TECHNIQUE "," SOC TECH ", 1)
    standard_name = standard_name.replace(" SDRUZENI PODNIKU "," SP ", 1)
    standard_name = standard_name.replace(" SDRUZENI PODNIK "," SP ", 1)
    standard_name = standard_name.replace(" SOCIETA PER AZIONI "," SPA ", 1)
    standard_name = standard_name.replace(" SPITALUL "," SPITAL ", 1)
    standard_name = standard_name.replace(" SOCIETE PRIVEE A RESPONSABILITE LIMITEE "," SPRL ", 1)
    standard_name = standard_name.replace(" SOCIEDAD DE RESPONSABILIDAD LIMITADA "," SRL ", 1)
    standard_name = standard_name.replace(" STIINTIFICA "," STIINT ", 1)
    standard_name = standard_name.replace(" SUDDEUTSCHES "," SUDDEUT ", 1)
    standard_name = standard_name.replace(" SUDDEUTSCHER "," SUDDEUT ", 1)
    standard_name = standard_name.replace(" SUDDEUTSCHE "," SUDDEUT ", 1)
    standard_name = standard_name.replace(" SUDDEUTSCH "," SUDDEUT ", 1)
    standard_name = standard_name.replace(" SOCIEDADE "," SOC ", 1)
    standard_name = standard_name.replace(" SOCIEDAD "," SOC ", 1)
    standard_name = standard_name.replace(" SOCIETA "," SOC ", 1)
    standard_name = standard_name.replace(" SOCIETE "," SOC ", 1)
    standard_name = standard_name.replace(" SOCIETY "," SOC ", 1)
    standard_name = standard_name.replace(" SA DITE "," SA ", 1)
    standard_name = standard_name.replace(" TECHNICAL "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNICO "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNICZNY "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNIKAI "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNIKI "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNIK "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNIQUES "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNIQUE "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNISCHES "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNISCHE "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNISCH "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNOLOGY "," TECH ", 1)
    standard_name = standard_name.replace(" TECHNOLOGIES "," TECH ", 1)
    standard_name = standard_name.replace(" TELECOMMUNICATIONS "," TELECOM ", 1)
    standard_name = standard_name.replace(" TELECOMMUNICACION "," TELECOM ", 1)
    standard_name = standard_name.replace(" TELECOMMUNICATION "," TELECOM ", 1)
    standard_name = standard_name.replace(" TELECOMMUNICAZIONI "," TELECOM ", 1)
    standard_name = standard_name.replace(" TELECOMUNICAZIONI "," TELECOM ", 1)
    standard_name = standard_name.replace(" TRUSTUL "," TRUST ", 1)
    standard_name = standard_name.replace(" UNITED KINGDOM "," UK ", 1)
    standard_name = standard_name.replace(" SECRETARY OF STATE FOR "," UK SEC FOR ", 1)
    standard_name = standard_name.replace(" UNIVERSIDADE "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSIDAD "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITA DEGLI STUDI "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITAET "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITAIRE "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITAIR "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITATEA "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITEIT "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITETAMI "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITETAM "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITETE "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITETOM "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITETOV "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITETU "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITETY "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITETA "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITAT "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITET "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITE "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITY "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIVERSITA "," UNIV ", 1)
    standard_name = standard_name.replace(" UNIWERSYTET "," UNIV ", 1)
    standard_name = standard_name.replace(" UNITED STATES OF AMERICA ADMINISTRATOR "," US ADMIN ", 1)
    standard_name = standard_name.replace(" UNITED STATES OF AMERICA AS REPRESENTED BY THE ADMINISTRATOR "," US ADMIN ", 1)
    standard_name = standard_name.replace(" UNITED STATES OF AMERICA AS REPRESENTED BY THE DEPT "," US DEPT ", 1)
    standard_name = standard_name.replace(" UNITED STATES OF AMERICA AS REPRESENTED BY THE UNITED STATES DEPT "," US DEPT ", 1)
    standard_name = standard_name.replace(" UNITED STATES OF AMERICAN AS REPRESENTED BY THE UNITED STATES DEPT "," US DEPT ", 1)
    standard_name = standard_name.replace(" UNITED STATES GOVERNMENT AS REPRESENTED BY THE SECRETARY OF "," US SEC ", 1)
    standard_name = standard_name.replace(" UNITED STATES OF AMERICA REPRESENTED BY THE SECRETARY "," US SEC ", 1)
    standard_name = standard_name.replace(" UNITED STATES OF AMERICA AS REPRESENTED BY THE SECRETARY "," US SEC ", 1)
    standard_name = standard_name.replace(" UNITED STATES OF AMERICAS AS REPRESENTED BY THE SECRETARY "," US SEC ", 1)
    standard_name = standard_name.replace(" UNITES STATES OF AMERICA AS REPRESENTED BY THE SECRETARY "," US SEC ", 1)
    standard_name = standard_name.replace(" UNITED STATES OF AMERICA SECRETARY OF "," US SEC ", 1)
    standard_name = standard_name.replace(" UNITED STATES OF AMERICA "," USA ", 1)
    standard_name = standard_name.replace(" UNITED STATES "," USA ", 1)
    standard_name = standard_name.replace(" UTILAJE "," UTIL ", 1)
    standard_name = standard_name.replace(" UTILAJ "," UTIL ", 1)
    standard_name = standard_name.replace(" UTILISATIONS VOLKSEIGENER BETRIEBE "," VEB ", 1)
    standard_name = standard_name.replace(" UTILISATION VOLKSEIGENER BETRIEBE "," VEB ", 1)
    standard_name = standard_name.replace(" VEB KOMBINAT "," VEB KOMB ", 1)
    standard_name = standard_name.replace(" VEREENIGDE "," VER ", 1)
    standard_name = standard_name.replace(" VEREINIGTES VEREINIGUNG "," VER ", 1)
    standard_name = standard_name.replace(" VEREINIGTE VEREINIGUNG "," VER ", 1)
    standard_name = standard_name.replace(" VEREIN "," VER ", 1)
    standard_name = standard_name.replace(" VERENIGING "," VER ", 1)
    standard_name = standard_name.replace(" VERWALTUNGEN "," VERW ", 1)
    standard_name = standard_name.replace(" VERWALTUNGS "," VERW ", 1)
    standard_name = standard_name.replace(" VERWERTUNGS "," VERW ", 1)
    standard_name = standard_name.replace(" VERWALTUNGSGESELLSCHAFT "," VERW GES ", 1)
    standard_name = standard_name.replace(" VYZK USTAV "," VU ", 1)
    standard_name = standard_name.replace(" VYZKUMNY USTAV "," VU ", 1)
    standard_name = standard_name.replace(" VYZKUMNYUSTAV "," VU ", 1)
    standard_name = standard_name.replace(" VEREINIGUNG VOLKSEIGENER BETRIEBUNG "," VVB ", 1)
    standard_name = standard_name.replace(" VYZK VYVOJOVY USTAV "," VVU ", 1)
    standard_name = standard_name.replace(" VYZKUMNY VYVOJOVY USTAV "," VVU ", 1)
    standard_name = standard_name.replace(" WERKZEUGMASCHINENKOMBINAT "," WERKZ MASCH KOMB ", 1)
    standard_name = standard_name.replace(" WERKZEUGMASCHINENFABRIK "," WERKZ MASCHFAB ", 1)
    standard_name = standard_name.replace(" WESTDEUTSCHES "," WESTDEUT ", 1)
    standard_name = standard_name.replace(" WESTDEUTSCHER "," WESTDEUT ", 1)
    standard_name = standard_name.replace(" WESTDEUTSCHE "," WESTDEUT ", 1)
    standard_name = standard_name.replace(" WESTDEUTSCH "," WESTDEUT ", 1)
    standard_name = standard_name.replace(" WISSENSCHAFTLICHE(S) "," WISS ", 1)
    standard_name = standard_name.replace(" WISSENSCHAFTLICHES TECHNISCHES ZENTRUM "," WTZ ", 1)
    standard_name = standard_name.replace(" YUGEN KAISHA "," YG YUGEN GAISHA ", 1)
    standard_name = standard_name.replace(" YUUGEN GAISHA "," YG YUGEN GAISHA ", 1)
    standard_name = standard_name.replace(" YUUGEN KAISHA "," YG YUGEN GAISHA ", 1)
    standard_name = standard_name.replace(" YUUGEN KAISYA "," YG YUGEN GAISHA ", 1)
    standard_name = standard_name.replace(" ZAVODU "," ZAVOD ", 1)
    standard_name = standard_name.replace(" ZAVODY "," ZAVOD ", 1)
    standard_name = standard_name.replace(" ZENTRALES "," ZENT ", 1)
    standard_name = standard_name.replace(" ZENTRALE "," ZENT ", 1)
    standard_name = standard_name.replace(" ZENTRALEN "," ZENT ", 1)
    standard_name = standard_name.replace(" ZENTRALNA "," ZENT ", 1)
    standard_name = standard_name.replace(" ZENTRUM "," ZENT ", 1)
    standard_name = standard_name.replace(" ZENTRALINSTITUT "," ZENT INST ", 1)
    standard_name = standard_name.replace(" ZENTRALLABORATORIUM "," ZENT LAB ", 1)
    standard_name = standard_name.replace(" ZAIDAN HOJIN "," ZH ", 1)
    standard_name = standard_name.replace(" ZAIDAN HOUJIN "," ZH ", 1)
    standard_name = standard_name.replace(" LIMITED "," LTD ", 1)
    standard_name = standard_name.replace(" LIMITADA "," LTDA ", 1)
    standard_name = standard_name.replace(" SECRETARY "," SEC ", 1)
    return(standard_name)


####################################################
# PROCEDURE 2 CREATE STANDARD NAME                 #
####################################################

def standard_naming(standard_name):
    # =============================================================================
    # ******************************************************************************************************
    # ** PROCEDURE 2 CREATE STANDARD NAME
    # **
    # ** This section standardises the way in which the type of legal entity is idenitified. For example
    # ** LIMITED is converted to LTD. These identifiers are country specific and, therefore, this is
    # ** section is organised by country.
    # ** It does this by, first, using the Derwent system and then doing some of our own country specific
    # ** changes that are important. The specific changes come from sources such as Dinesh's code, Bronwyn's code
    # ** and other files we have for Germany, France and Sweden from various other people.
    # ** Additions made for USPTO dataset by BHH  August 2006
    # **
    # ******************************************************************************************************
    # =============================================================================

    # Onw constribution: Keep standardized string format for main routine
    standard_name = ' '+standard_name.upper().strip()+' '

    #** 1) Call Derwent code
    standard_name = derwent_standard_name(standard_name)

    #** 2) Perform some additional changes
    standard_name = standard_name.replace(" RES & DEV ", " R&D ", 1)
    standard_name = standard_name.replace(" RECH & DEV ", " R&D ", 1)

    # 3) Perform some country specific work
    # UNITED STATES (most of this is in Derwent)

    # UNITED KINGDOM
    standard_name = standard_name.replace(" PUBLIC LIMITED ", " PLC ", 1)
    standard_name = standard_name.replace(" PUBLIC LIABILITY COMPANY ", " PLC ", 1)
    standard_name = standard_name.replace(" HOLDINGS ", " HLDGS ", 1)
    standard_name = standard_name.replace(" HOLDING ", " HLDGS ", 1)
    standard_name = standard_name.replace(" GREAT BRITAIN ", " GB ", 1)
    standard_name = standard_name.replace(" LTD CO ", " CO LTD ", 1)

    # => no international context, so no need for adjustments outside US
    r'''
    # SPANISH
    standard_name = standard_name.replace(" SOC LIMITADA ", " SL ", 1)
    standard_name = standard_name.replace(" SOC EN COMMANDITA ", " SC ", 1)
    standard_name = standard_name.replace(" & CIA ", " CO ", 1)

    # ITALIAN
    standard_name = standard_name.replace(" SOC IN ACCOMANDITA PER AZIONI ", " SA ", 1)
    standard_name = standard_name.replace(" SAPA ", " SA ", 1)
    standard_name = standard_name.replace(" SOC A RESPONSABILIT� LIMITATA ", " SRL ", 1)

    # SWEDISH
    standard_name = standard_name.replace(" HANDELSBOLAG ", " HB  ", 1)

    # GERMAN
    standard_name = standard_name.replace(" KOMANDIT GESELLSCHAFT ", " KG ", 1)
    standard_name = standard_name.replace(" KOMANDITGESELLSCHAFT ", " KG ", 1)
    standard_name = standard_name.replace(" EINGETRAGENE GENOSSENSCHAFT ", " EG ", 1)
    standard_name = standard_name.replace(" GENOSSENSCHAFT ", " EG ", 1)
    standard_name = standard_name.replace(" GESELLSCHAFT M B H ", " GMBH ", 1)
    standard_name = standard_name.replace(" OFFENE HANDELS GESELLSCHAFT ", " OHG ", 1)
    standard_name = standard_name.replace(" GESMBH ", " GMBH ", 1)
    standard_name = standard_name.replace(" GESELLSCHAFT BURGERLICHEN RECHTS ", " GBR ", 1)
    standard_name = standard_name.replace(" GESELLSCHAFT ", " GMBH ", 1)
    # The following is common format. If conflict assume GMBH & CO KG over GMBH & CO OHG as more common.
    standard_name = standard_name.replace(" GMBH CO KG ", " GMBH & CO KG ", 1)
    standard_name = standard_name.replace(" GMBH COKG ", " GMBH & CO KG ", 1)
    standard_name = standard_name.replace(" GMBH U CO KG ", " GMBH & CO KG ", 1)
    standard_name = standard_name.replace(" GMBH U COKG ", " GMBH & CO KG ", 1)
    standard_name = standard_name.replace(" GMBH U CO ", " GMBH & CO KG ", 1)
    standard_name = standard_name.replace(" GMBH CO ", " GMBH & CO KG ", 1)
    standard_name = standard_name.replace(" AG CO KG ", " AG & CO KG ", 1)
    standard_name = standard_name.replace(" AG COKG ", " AG & CO KG ", 1)
    standard_name = standard_name.replace(" AG U CO KG ", " AG & CO KG ", 1)
    standard_name = standard_name.replace(" AG U COKG ", " AG & CO KG ", 1)
    standard_name = standard_name.replace(" AG U CO ", " AG & CO KG ", 1)
    standard_name = standard_name.replace(" AG CO ", " AG & CO KG ", 1)
    standard_name = standard_name.replace(" GMBH CO OHG ", " GMBH &CO OHG ", 1)
    standard_name = standard_name.replace(" GMBH COOHG ", " GMBH & CO OHG ", 1)
    standard_name = standard_name.replace(" GMBH U CO OHG ", " GMBH & CO OHG ", 1)
    standard_name = standard_name.replace(" GMBH U COOHG ", " GMBH & CO OHG ", 1)
    standard_name = standard_name.replace(" AG CO OHG ", " AG & CO OHG ", 1)
    standard_name = standard_name.replace(" AG COOHG ", " AG & CO OHG ", 1)
    standard_name = standard_name.replace(" AG U CO OHG ", " AG & CO OHG ", 1)
    standard_name = standard_name.replace(" AG U COOHG ", " AG & CO OHG ", 1)

    # FRENCH and BELGIAN
    standard_name = standard_name.replace(" SOCIETE ANONYME SIMPLIFIEE ", " SAS ", 1)
    standard_name = standard_name.replace(" SOC ANONYME ", " SA ", 1)
    standard_name = standard_name.replace(" STE ANONYME ", " SA ", 1)
    standard_name = standard_name.replace(" SARL UNIPERSONNELLE ", " SARLU ", 1)
    standard_name = standard_name.replace(" SOC PAR ACTIONS SIMPLIFIEES ", " SAS ", 1)
    standard_name = standard_name.replace(" SAS UNIPERSONNELLE ", " SASU ", 1)
    standard_name = standard_name.replace(" ENTREPRISE UNIPERSONNELLE A RESPONSABILITE LIMITEE ", " EURL ", 1)
    standard_name = standard_name.replace(" SOCIETE CIVILE IMMOBILIERE ", " SCI ", 1)
    standard_name = standard_name.replace(" GROUPEMENT D INTERET ECONOMIQUE ", " GIE ", 1)
    standard_name = standard_name.replace(" SOCIETE EN PARTICIPATION ", " SP ", 1)
    standard_name = standard_name.replace(" SOCIETE EN COMMANDITE SIMPLE ", " SCS ", 1)
    standard_name = standard_name.replace(" ANONYME DITE ", " SA ", 1)
    standard_name = standard_name.replace(" SOC DITE ", " SA ", 1)
    standard_name = standard_name.replace(" & CIE ", " CO ", 1)

    # BELGIAN
    # Note: the Belgians use a lot of French endings, so handle as above.
    # Also, they use NV (belgian) and SA (french) interchangably, so standardise to SA

    standard_name = standard_name.replace(" BV BEPERKTE AANSPRAKELIJKHEID ", " BVBA ", 1)
    standard_name = standard_name.replace(" COMMANDITAIRE VENNOOTSCHAP OP AANDELEN ", " CVA ", 1)
    standard_name = standard_name.replace(" GEWONE COMMANDITAIRE VENNOOTSCHAP ", " GCV ", 1)
    standard_name = standard_name.replace(" SOCIETE EN COMMANDITE PAR ACTIONS ", " SCA ", 1)

    #* Change to French language equivalents where appropriate
    #* Don't do this for now
    #*standard_name = standard_name.replace(" GCV ", " SCS ", 1)
    #*standard_name = standard_name.replace(" NV ", " SA ", 1)
    #*standard_name = standard_name.replace(" BVBA ", " SPRL ", 1)

    # DENMARK
    #* Usually danish identifiers have a slash (eg. A/S or K/S), but these will have been removed with all
    #* other punctuation earlier (so just use AS or KS).
    standard_name = standard_name.replace(" ANDELSSELSKABET ", " AMBA ", 1)
    standard_name = standard_name.replace(" ANDELSSELSKAB ", " AMBA ", 1)
    standard_name = standard_name.replace(" INTERESSENTSKABET ", " IS ", 1)
    standard_name = standard_name.replace(" INTERESSENTSKAB ", " IS ", 1)
    standard_name = standard_name.replace(" KOMMANDITAKTIESELSKABET ", " KAS ", 1)
    standard_name = standard_name.replace(" KOMMANDITAKTIESELSKAB ", " KAS ", 1)
    standard_name = standard_name.replace(" KOMMANDITSELSKABET ", " KS ", 1)
    standard_name = standard_name.replace(" KOMMANDITSELSKAB ", " KS ", 1)

    # NORWAY
    standard_name = standard_name.replace(" ANDELSLAGET ", " AL ", 1)
    standard_name = standard_name.replace(" ANDELSLAG ", " AL ", 1)
    standard_name = standard_name.replace(" ANSVARLIG SELSKAPET ", " ANS ", 1)
    standard_name = standard_name.replace(" ANSVARLIG SELSKAP ", " ANS ", 1)
    standard_name = standard_name.replace(" AKSJESELSKAPET ", " AS ", 1)
    standard_name = standard_name.replace(" AKSJESELSKAP ", " AS ", 1)
    standard_name = standard_name.replace(" ALLMENNAKSJESELSKAPET ", " ASA ", 1)
    standard_name = standard_name.replace(" ALLMENNAKSJESELSKAP ", " ASA ", 1)
    standard_name = standard_name.replace(" SELSKAP MED DELT ANSAR ", " DA ", 1)
    standard_name = standard_name.replace(" KOMMANDITTSELSKAPET ", " KS ", 1)
    standard_name = standard_name.replace(" KOMMANDITTSELSKAP ", " KS ", 1)

    # NETHERLANDS
    standard_name = standard_name.replace(" COMMANDITAIRE VENNOOTSCHAP ", " CV ", 1)
    standard_name = standard_name.replace(" COMMANDITAIRE VENNOOTSCHAP OP ANDELEN ", " CVOA ", 1)
    standard_name = standard_name.replace(" VENNOOTSCHAP ONDER FIRMA ", " VOF ", 1)

    # FINLAND
    standard_name = standard_name.replace(" PUBLIKT AKTIEBOLAG ", " APB ", 1)
    standard_name = standard_name.replace(" KOMMANDIITTIYHTIO ", " KY ", 1)
    standard_name = standard_name.replace(" JULKINEN OSAKEYHTIO ", " OYJ ", 1)

    # POLAND
    standard_name = standard_name.replace(" SPOLKA AKCYJNA ", " SA ", 1)
    standard_name = standard_name.replace(" SPOLKA PRAWA CYWILNEGO ", " SC ", 1)
    standard_name = standard_name.replace(" SPOLKA KOMANDYTOWA ", " SK ", 1)
    standard_name = standard_name.replace(" SPOLKA Z OGRANICZONA ODPOWIEDZIALNOSCIA ", " SPZOO ", 1)
    standard_name = standard_name.replace(" SP Z OO ", " SPZOO ", 1)
    standard_name = standard_name.replace(" SPZ OO ", " SPZOO ", 1)
    standard_name = standard_name.replace(" SP ZOO ", " SPZOO ", 1)

    # GREECE
    standard_name = standard_name.replace(" ANONYMOS ETAIRIA ", " AE ", 1)
    standard_name = standard_name.replace(" ETERRORRYTHMOS ", " EE ", 1)
    standard_name = standard_name.replace(" ETAIRIA PERIORISMENIS EVTHINIS ", " EPE ", 1)
    standard_name = standard_name.replace(" OMORRYTHMOS ", " OE ", 1)

    # CZECH REPUBLIC
    standard_name = standard_name.replace(" AKCIOVA SPOLECNOST ", " AS ", 1)
    standard_name = standard_name.replace(" KOMANDITNI SPOLECNOST ", " KS ", 1)
    standard_name = standard_name.replace(" SPOLECNOST S RUCENIM OMEZENYM ", " SRO ", 1)
    standard_name = standard_name.replace(" VEREJNA OBCHODNI SPOLECNOST ", " VOS ", 1)

    # BULGARIA
    standard_name = standard_name.replace(" AKTIONIERNO DRUSHESTWO ", " AD ", 1)
    standard_name = standard_name.replace(" KOMANDITNO DRUSHESTWO ", " KD ", 1)
    standard_name = standard_name.replace(" KOMANDITNO DRUSHESTWO S AKZII ", " KDA ", 1)
    standard_name = standard_name.replace(" DRUSHESTWO S ORGRANITSCHENA OTGOWORNOST ", " OCD ", 1)
    r'''
    return(standard_name)


# %%
####################################################
# Procedure 3 IDENTIFY CORPORATES                  #
####################################################

def corporates_bool(standard_name):
    # =============================================================================
    # ************************************************************************************************
    # ** Procedure 3 IDENTIFY CORPORATES
    # **
    # ** This section attempts to identify corporates by looking for words such as "INC".
    # ** A flag is set if such words are found.
    # ** Recode of non-corporates by BHH to use KUL list of company terms.
    # * jb 1/15/08 index=>strpos
    # ************************************************************************************************
    # =============================================================================

    # Onw constribution, first stip leading and trailing white space and translate to lower
    # Then add white space around string to match description, needed for working with the strings
    standard_name = ' '+standard_name.upper().strip()+' '

    type_firm = False
    type_firm += bool(" & BRO " in standard_name)
    type_firm += bool(" & BROTHER " in standard_name)
    type_firm += bool(" & C " in standard_name)
    type_firm += bool(" & CIE " in standard_name)
    type_firm += bool(" & CO " in standard_name)
    type_firm += bool(" & FILS " in standard_name)
    type_firm += bool(" & PARTNER " in standard_name)
    type_firm += bool(" & SOEHNE " in standard_name)
    type_firm += bool(" & SOHN " in standard_name)
    type_firm += bool(" & SON " in standard_name)
    type_firm += bool(" & SONS " in standard_name)
    type_firm += bool(" & ZN " in standard_name)
    type_firm += bool(" & ZONEN " in standard_name)
    type_firm += bool(" A " in standard_name)
    type_firm += bool(" A G " in standard_name)
    type_firm += bool(" A RL " in standard_name)
    type_firm += bool(" A S " in standard_name)
    type_firm += bool(" AANSPRAKELIJKHEID " in standard_name)
    type_firm += bool(" AB " in standard_name)
    type_firm += bool(" ACTIEN GESELLSCHAFT " in standard_name)
    type_firm += bool(" ACTIENGESELLSCHAFT " in standard_name)
    type_firm += bool(" AD " in standard_name)
    type_firm += bool(" ADVIESBUREAU " in standard_name)
    type_firm += bool(" AE " in standard_name)
    type_firm += bool(" AG " in standard_name)
    type_firm += bool(" AG & CO " in standard_name)
    type_firm += bool(" AGG " in standard_name)
    type_firm += bool(" AGSA " in standard_name)
    type_firm += bool(" AK TIEBOLAGET " in standard_name)
    type_firm += bool(" AKIEBOLAG " in standard_name)
    type_firm += bool(" AKIEBOLG " in standard_name)
    type_firm += bool(" AKIENGESELLSCHAFT " in standard_name)
    type_firm += bool(" AKITENGESELLSCHAFT " in standard_name)
    type_firm += bool(" AKITIEBOLAG " in standard_name)
    type_firm += bool(" AKLIENGISELLSCHAFT " in standard_name)
    type_firm += bool(" AKSJESELSKAP " in standard_name)
    type_firm += bool(" AKSJESELSKAPET " in standard_name)
    type_firm += bool(" AKSTIEBOLAGET " in standard_name)
    type_firm += bool(" AKTAINGESELLSCHAFT " in standard_name)
    type_firm += bool(" AKTEIBOLAG " in standard_name)
    type_firm += bool(" AKTEINGESELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIBOLAG " in standard_name)
    type_firm += bool(" AKTIE BOLAGET " in standard_name)
    type_firm += bool(" AKTIEBDAG " in standard_name)
    type_firm += bool(" AKTIEBLOAG " in standard_name)
    type_firm += bool(" AKTIEBOALG " in standard_name)
    type_firm += bool(" AKTIEBOALGET " in standard_name)
    type_firm += bool(" AKTIEBOCAG " in standard_name)
    type_firm += bool(" AKTIEBOLAC " in standard_name)
    type_firm += bool(" AKTIEBOLAF " in standard_name)
    type_firm += bool(" AKTIEBOLAG " in standard_name)
    type_firm += bool(" AKTIEBOLAGET " in standard_name)
    type_firm += bool(" AKTIEBOLAQ " in standard_name)
    type_firm += bool(" AKTIEBOLOG " in standard_name)
    type_firm += bool(" AKTIEGBOLAG " in standard_name)
    type_firm += bool(" AKTIEGESELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIEGOLAGET " in standard_name)
    type_firm += bool(" AKTIELBOLAG " in standard_name)
    type_firm += bool(" AKTIEN " in standard_name)
    type_firm += bool(" AKTIEN GESELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENBOLAG " in standard_name)
    type_firm += bool(" AKTIENBOLAGET " in standard_name)
    type_firm += bool(" AKTIENEGESELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENEGSELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGEGESELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESCELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESELL SCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESELLCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESELLESCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESELLESHAFT " in standard_name)
    type_firm += bool(" AKTIENGESELLS " in standard_name)
    type_firm += bool(" AKTIENGESELLSCAFT " in standard_name)
    type_firm += bool(" AKTIENGESELLSCGAFT " in standard_name)
    type_firm += bool(" AKTIENGESELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESELLSCHART " in standard_name)
    type_firm += bool(" AKTIENGESELLSCHATT " in standard_name)
    type_firm += bool(" AKTIENGESELLSCHGT " in standard_name)
    type_firm += bool(" AKTIENGESELLSCHRAFT " in standard_name)
    type_firm += bool(" AKTIENGESELLSHAFT " in standard_name)
    type_firm += bool(" AKTIENGESELLSHAT " in standard_name)
    type_firm += bool(" AKTIENGESELLSHCAFT " in standard_name)
    type_firm += bool(" AKTIENGESELSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESESCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESILLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESLLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESSELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGESSELSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGSELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENGTESELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIENRESELLSCHAFT " in standard_name)
    type_firm += bool(" AKTIESELSKAB " in standard_name)
    type_firm += bool(" AKTIESELSKABET " in standard_name)
    type_firm += bool(" AKTINGESELLSCHAFT " in standard_name)
    type_firm += bool(" AKTSIONERNAYA KOMPANIA " in standard_name)
    type_firm += bool(" AKTSIONERNO " in standard_name)
    type_firm += bool(" AKTSIONERNOE OBCHESTVO " in standard_name)
    type_firm += bool(" AKTSIONERNOE OBSCHEDTVO " in standard_name)
    type_firm += bool(" AKTSIONERNOE OBSCNESTVO " in standard_name)
    type_firm += bool(" AKTSIONERNOE OBSHESTVO " in standard_name)
    type_firm += bool(" AKTSIONERNOE OSBCHESTVO " in standard_name)
    type_firm += bool(" AKTSIONERNOEOBSCHESTVO " in standard_name)
    type_firm += bool(" ALTIENGESELLSCHAFT " in standard_name)
    type_firm += bool(" AMBA " in standard_name)
    type_firm += bool(" AND SONS " in standard_name)
    type_firm += bool(" ANDELSSELSKABET " in standard_name)
    type_firm += bool(" ANLAGENGESELLSCHAFT " in standard_name)
    type_firm += bool(" APPARATEBAU " in standard_name)
    type_firm += bool(" APPERATEBAU " in standard_name)
    type_firm += bool(" ARL " in standard_name)
    type_firm += bool(" AS " in standard_name)
    type_firm += bool(" ASA " in standard_name)
    type_firm += bool(" ASKTIENGESELLSCHAFT " in standard_name)
    type_firm += bool(" ASOCIADOS " in standard_name)
    type_firm += bool(" ASSCOIATES " in standard_name)
    type_firm += bool(" ASSOCIADOS " in standard_name)
    type_firm += bool(" ASSOCIATE " in standard_name)
    type_firm += bool(" ASSOCIATED " in standard_name)
    type_firm += bool(" ASSOCIATES " in standard_name)
    type_firm += bool(" ASSOCIATI " in standard_name)
    type_firm += bool(" ASSOCIATO " in standard_name)
    type_firm += bool(" ASSOCIES " in standard_name)
    type_firm += bool(" ASSSOCIATES " in standard_name)
    type_firm += bool(" ATELIER " in standard_name)
    type_firm += bool(" ATELIERS " in standard_name)
    type_firm += bool(" ATIBOLAG " in standard_name)
    type_firm += bool(" ATKIEBOLAG " in standard_name)
    type_firm += bool(" ATKIENGESELLSCHAFT " in standard_name)
    type_firm += bool(" AVV " in standard_name)
    type_firm += bool(" B " in standard_name)
    type_firm += bool(" BANK " in standard_name)
    type_firm += bool(" BANQUE " in standard_name)
    type_firm += bool(" BEDRIJF " in standard_name)
    type_firm += bool(" BEDRIJVEN " in standard_name)
    type_firm += bool(" BEPERK " in standard_name)
    type_firm += bool(" BEPERKTE AANSPREEKLIJKHEID " in standard_name)
    type_firm += bool(" BESCHRAENKTER HAFTUNG " in standard_name)
    type_firm += bool(" BESCHRANKTER " in standard_name)
    type_firm += bool(" BESCHRANKTER HAFTUNG " in standard_name)
    type_firm += bool(" BESLOTENGENOOTSCHAP " in standard_name)
    type_firm += bool(" BESLOTENVENNOOTSCHAP " in standard_name)
    type_firm += bool(" BETRIEBE " in standard_name)
    type_firm += bool(" BMBH " in standard_name)
    type_firm += bool(" BRANDS " in standard_name)
    type_firm += bool(" BROS " in standard_name)
    type_firm += bool(" BUSINESS " in standard_name)
    type_firm += bool(" BV " in standard_name)
    type_firm += bool(" BV: " in standard_name)
    type_firm += bool(" BV? " in standard_name)
    type_firm += bool(" BVBA " in standard_name)
    type_firm += bool(" BVBASPRL " in standard_name)
    type_firm += bool(" BVIO " in standard_name)
    type_firm += bool(" BVSA " in standard_name)
    type_firm += bool(" C{OVERSCORE O}RP " in standard_name)
    type_firm += bool(" CAMPAGNIE " in standard_name)
    type_firm += bool(" CAMPANY " in standard_name)
    type_firm += bool(" CC " in standard_name)
    type_firm += bool(" CIE " in standard_name)
    type_firm += bool(" CMOPANY " in standard_name)
    type_firm += bool(" CO " in standard_name)
    type_firm += bool(" CO OPERATIVE " in standard_name)
    type_firm += bool(" CO OPERATIVES " in standard_name)
    type_firm += bool(" CO: " in standard_name)
    type_firm += bool(" COFP " in standard_name)
    type_firm += bool(" COIRPORATION " in standard_name)
    type_firm += bool(" COMANY " in standard_name)
    type_firm += bool(" COMAPANY " in standard_name)
    type_firm += bool(" COMERCIAL " in standard_name)
    type_firm += bool(" COMERCIO " in standard_name)
    type_firm += bool(" COMMANDITE SIMPLE " in standard_name)
    type_firm += bool(" COMMERCIALE " in standard_name)
    type_firm += bool(" COMMERCIALISATIONS " in standard_name)
    type_firm += bool(" COMNPANY " in standard_name)
    type_firm += bool(" COMP " in standard_name)
    type_firm += bool(" COMPAGNE " in standard_name)
    type_firm += bool(" COMPAGNI " in standard_name)
    type_firm += bool(" COMPAGNIE " in standard_name)
    type_firm += bool(" COMPAGNIN " in standard_name)
    type_firm += bool(" COMPAGNY " in standard_name)
    type_firm += bool(" COMPAIGNIE " in standard_name)
    type_firm += bool(" COMPAMY " in standard_name)
    type_firm += bool(" COMPANAY " in standard_name)
    type_firm += bool(" COMPANH " in standard_name)
    type_firm += bool(" COMPANHIA " in standard_name)
    type_firm += bool(" COMPANIA " in standard_name)
    type_firm += bool(" COMPANIE " in standard_name)
    type_firm += bool(" COMPANIES " in standard_name)
    type_firm += bool(" COMPANY " in standard_name)
    type_firm += bool(" COMPAY " in standard_name)
    type_firm += bool(" COMPNAY " in standard_name)
    type_firm += bool(" COMAPNY " in standard_name)
    type_firm += bool(" COMPNY " in standard_name)
    type_firm += bool(" COMPORATION " in standard_name)
    type_firm += bool(" CONSORTILE PER AZIONE " in standard_name)
    type_firm += bool(" CONSORZIO " in standard_name)
    type_firm += bool(" CONSTRUCTIONS " in standard_name)
    type_firm += bool(" CONSULTING " in standard_name)
    type_firm += bool(" CONZORZIO " in standard_name)
    type_firm += bool(" COOEPERATIE " in standard_name)
    type_firm += bool(" COOEPERATIEVE " in standard_name)
    type_firm += bool(" COOEPERATIEVE VERENIGING " in standard_name)
    type_firm += bool(" COOEPERATIEVE VERKOOP " in standard_name)
    type_firm += bool(" COOP " in standard_name)
    type_firm += bool(" COOP A RL " in standard_name)
    type_firm += bool(" COOPERATIE " in standard_name)
    type_firm += bool(" COOPERATIEVE " in standard_name)
    type_firm += bool(" COOPERATIEVE VENOOTSCHAP " in standard_name)
    type_firm += bool(" COOPERATION " in standard_name)
    type_firm += bool(" COOPERATIVA AGICOLA " in standard_name)
    type_firm += bool(" COOPERATIVA LIMITADA " in standard_name)
    type_firm += bool(" COOPERATIVA PER AZIONI " in standard_name)
    type_firm += bool(" COORPORATION " in standard_name)
    type_firm += bool(" COPANY " in standard_name)
    type_firm += bool(" COPORATION " in standard_name)
    type_firm += bool(" COPR " in standard_name)
    type_firm += bool(" COPRORATION " in standard_name)
    type_firm += bool(" COPRPORATION " in standard_name)
    type_firm += bool(" COROPORTION " in standard_name)
    type_firm += bool(" COROPRATION " in standard_name)
    type_firm += bool(" COROPROATION " in standard_name)
    type_firm += bool(" CORORATION " in standard_name)
    type_firm += bool(" CORP " in standard_name)
    type_firm += bool(" CORPARATION " in standard_name)
    type_firm += bool(" CORPERATION " in standard_name)
    type_firm += bool(" CORPFORATION " in standard_name)
    type_firm += bool(" CORPN " in standard_name)
    type_firm += bool(" CORPO " in standard_name)
    type_firm += bool(" CORPOARTION " in standard_name)
    type_firm += bool(" CORPOATAION " in standard_name)
    type_firm += bool(" CORPOATION " in standard_name)
    type_firm += bool(" CORPOIRATION " in standard_name)
    type_firm += bool(" CORPOORATION " in standard_name)
    type_firm += bool(" CORPOPRATION " in standard_name)
    type_firm += bool(" CORPORAATION " in standard_name)
    type_firm += bool(" CORPORACION " in standard_name)
    type_firm += bool(" CORPORAION " in standard_name)
    type_firm += bool(" CORPORAITON " in standard_name)
    type_firm += bool(" CORPORARION " in standard_name)
    type_firm += bool(" CORPORARTION " in standard_name)
    type_firm += bool(" CORPORATAION " in standard_name)
    type_firm += bool(" CORPORATE " in standard_name)
    type_firm += bool(" CORPORATED " in standard_name)
    type_firm += bool(" CORPORATI " in standard_name)
    type_firm += bool(" CORPORATIION " in standard_name)
    type_firm += bool(" CORPORATIN " in standard_name)
    type_firm += bool(" CORPORATINO " in standard_name)
    type_firm += bool(" CORPORATINON " in standard_name)
    type_firm += bool(" CORPORATIO " in standard_name)
    type_firm += bool(" CORPORATIOIN " in standard_name)
    type_firm += bool(" CORPORATIOLN " in standard_name)
    type_firm += bool(" CORPORATIOM " in standard_name)
    type_firm += bool(" CORPORATION " in standard_name)
    type_firm += bool(" CORPORATIOPN " in standard_name)
    type_firm += bool(" CORPORATITON " in standard_name)
    type_firm += bool(" CORPORATOIN " in standard_name)
    type_firm += bool(" CORPORDATION " in standard_name)
    type_firm += bool(" CORPORQTION " in standard_name)
    type_firm += bool(" CORPORTAION " in standard_name)
    type_firm += bool(" CORPORTATION " in standard_name)
    type_firm += bool(" CORPORTION " in standard_name)
    type_firm += bool(" CORPPORATION " in standard_name)
    type_firm += bool(" CORPRATION " in standard_name)
    type_firm += bool(" CORPROATION " in standard_name)
    type_firm += bool(" CORPRORATION " in standard_name)
    type_firm += bool(" CROP " in standard_name)
    type_firm += bool(" CROPORATION " in standard_name)
    type_firm += bool(" CRPORATION " in standard_name)
    type_firm += bool(" CV " in standard_name)
    type_firm += bool(" D ENTERPRISES " in standard_name)
    type_firm += bool(" D ENTREPRISE " in standard_name)
    type_firm += bool(" D O O " in standard_name)
    type_firm += bool(" D�ENTREPRISE " in standard_name)
    type_firm += bool(" DD " in standard_name)
    type_firm += bool(" DEVELOP " in standard_name)
    type_firm += bool(" DEVELOPPEMENT " in standard_name)
    type_firm += bool(" DEVELOPPEMENTS " in standard_name)
    type_firm += bool(" DOING BUSINESS " in standard_name)
    type_firm += bool(" DOO " in standard_name)
    type_firm += bool(" DORPORATION " in standard_name)
    type_firm += bool(" EDMS " in standard_name)
    type_firm += bool(" EG " in standard_name)
    type_firm += bool(" ELECTRONIQUE " in standard_name)
    type_firm += bool(" EN ZN " in standard_name)
    type_firm += bool(" EN ZONEN " in standard_name)
    type_firm += bool(" ENGINEERING " in standard_name)
    type_firm += bool(" ENGINEERS " in standard_name)
    type_firm += bool(" ENGINES " in standard_name)
    type_firm += bool(" ENNOBLISSEMENT " in standard_name)
    type_firm += bool(" ENTERPRISE " in standard_name)
    type_firm += bool(" ENTRE PRISES " in standard_name)
    type_firm += bool(" ENTREPOSE " in standard_name)
    type_firm += bool(" ENTREPRISE " in standard_name)
    type_firm += bool(" ENTREPRISES " in standard_name)
    type_firm += bool(" EQUIP " in standard_name)
    type_firm += bool(" EQUIPAMENTOS " in standard_name)
    type_firm += bool(" EQUIPEMENT " in standard_name)
    type_firm += bool(" EQUIPEMENTS " in standard_name)
    type_firm += bool(" EQUIPMENT " in standard_name)
    type_firm += bool(" EST " in standard_name)
    type_firm += bool(" ESTABILSSEMENTS " in standard_name)
    type_firm += bool(" ESTABLISHMENT " in standard_name)
    type_firm += bool(" ESTABLISSEMENT " in standard_name)
    type_firm += bool(" ESTABLISSEMENTS " in standard_name)
    type_firm += bool(" ESTABLISSMENTS " in standard_name)
    type_firm += bool(" ET FILS " in standard_name)
    type_firm += bool(" ETABLISSEMENT " in standard_name)
    type_firm += bool(" ETABLISSMENTS " in standard_name)
    type_firm += bool(" ETS " in standard_name)
    type_firm += bool(" FABRIC " in standard_name)
    type_firm += bool(" FABRICA " in standard_name)
    type_firm += bool(" FABRICATION " in standard_name)
    type_firm += bool(" FABRICATIONS " in standard_name)
    type_firm += bool(" FABRICS " in standard_name)
    type_firm += bool(" FABRIEKEN " in standard_name)
    type_firm += bool(" FABRIK " in standard_name)
    type_firm += bool(" FABRIQUE " in standard_name)
    type_firm += bool(" FABRYKA " in standard_name)
    type_firm += bool(" FACTORY " in standard_name)
    type_firm += bool(" FEDERATED " in standard_name)
    type_firm += bool(" FILM " in standard_name)
    type_firm += bool(" FINANCIERE " in standard_name)
    type_firm += bool(" FIRM " in standard_name)
    type_firm += bool(" FIRMA " in standard_name)
    type_firm += bool(" GBMH " in standard_name)
    type_firm += bool(" GBR " in standard_name)
    type_firm += bool(" GEBR " in standard_name)
    type_firm += bool(" GEBROEDERS " in standard_name)
    type_firm += bool(" GEBRUEDER " in standard_name)
    type_firm += bool(" GENERALE POUR LES TECHNIQUES NOUVELLE " in standard_name)
    type_firm += bool(" GENOSSENSCHAFT " in standard_name)
    type_firm += bool(" GES M B H " in standard_name)
    type_firm += bool(" GES MB H " in standard_name)
    type_firm += bool(" GES MBH " in standard_name)
    type_firm += bool(" GES MHH " in standard_name)
    type_firm += bool(" GESELLSCHAFT " in standard_name)
    type_firm += bool(" GESELLSCHAFT M B " in standard_name)
    type_firm += bool(" GESELLSCHAFT MB H " in standard_name)
    type_firm += bool(" GESELLSCHAFT MBH " in standard_name)
    type_firm += bool(" GESELLSCHAFT MGH " in standard_name)
    type_firm += bool(" GESELLSCHAFT MIT " in standard_name)
    type_firm += bool(" GESELLSCHAFT MIT BESCHRANKTER " in standard_name)
    type_firm += bool(" GESELLSCHAFT MIT BESCHRANKTER HAFT " in standard_name)
    type_firm += bool(" GESELLSCHAFTMIT BESCHRANKTER " in standard_name)
    type_firm += bool(" GESMBH " in standard_name)
    type_firm += bool(" GES " in standard_name)
    type_firm += bool(" GESSELLSCHAFT MIT BESCHRAENKTER HAUFTUNG " in standard_name)
    type_firm += bool(" GIE " in standard_name)
    type_firm += bool(" GMBA " in standard_name)
    type_firm += bool(" GMBB " in standard_name)
    type_firm += bool(" GMBG " in standard_name)
    type_firm += bool(" GMBH " in standard_name)
    type_firm += bool(" GMHB " in standard_name)
    type_firm += bool(" GNBH " in standard_name)
    type_firm += bool(" GORPORATION " in standard_name)
    type_firm += bool(" GROEP " in standard_name)
    type_firm += bool(" GROUP " in standard_name)
    type_firm += bool(" GROUPEMENT D ENTREPRISES " in standard_name)
    type_firm += bool(" H " in standard_name)
    type_firm += bool(" HAFRUNG " in standard_name)
    type_firm += bool(" HANDEL " in standard_name)
    type_firm += bool(" HANDELABOLAGET " in standard_name)
    type_firm += bool(" HANDELEND ONDER " in standard_name)
    type_firm += bool(" HANDELORGANISATION " in standard_name)
    type_firm += bool(" HANDELS " in standard_name)
    type_firm += bool(" HANDELSBOLAG " in standard_name)
    type_firm += bool(" HANDELSBOLAGET " in standard_name)
    type_firm += bool(" HANDELSGESELLSCHAFT " in standard_name)
    type_firm += bool(" HANDESBOLAG " in standard_name)
    type_firm += bool(" HATFUNG " in standard_name)
    type_firm += bool(" HB " in standard_name)
    type_firm += bool(" HF " in standard_name)
    type_firm += bool(" HOLDINGS " in standard_name)
    type_firm += bool(" INC " in standard_name)
    type_firm += bool(" INC: " in standard_name)
    type_firm += bool(" INCOPORATED " in standard_name)
    type_firm += bool(" INCORORATED " in standard_name)
    type_firm += bool(" INCORPARATED " in standard_name)
    type_firm += bool(" INCORPATED " in standard_name)
    type_firm += bool(" INCORPORATE " in standard_name)
    type_firm += bool(" INCORPORATED " in standard_name)
    type_firm += bool(" INCORPORORATED " in standard_name)
    type_firm += bool(" INCORPORTED " in standard_name)
    type_firm += bool(" INCORPOTATED " in standard_name)
    type_firm += bool(" INCORPRATED " in standard_name)
    type_firm += bool(" INCORPRORATED " in standard_name)
    type_firm += bool(" INCROPORATED " in standard_name)
    type_firm += bool(" INDISTRIES " in standard_name)
    type_firm += bool(" INDUSRTIES " in standard_name)
    type_firm += bool(" INDUSTRI " in standard_name)
    type_firm += bool(" INDUSTRIA " in standard_name)
    type_firm += bool(" INDUSTRIAL " in standard_name)
    type_firm += bool(" INDUSTRIAL COP " in standard_name)
    type_firm += bool(" INDUSTRIALNA " in standard_name)
    type_firm += bool(" INDUSTRIAS " in standard_name)
    type_firm += bool(" INDUSTRIE " in standard_name)
    type_firm += bool(" INDUSTRIES " in standard_name)
    type_firm += bool(" INDUSTRIJA " in standard_name)
    type_firm += bool(" INDUSTRIJSKO " in standard_name)
    type_firm += bool(" INGENIEURBUERO " in standard_name)
    type_firm += bool(" INGENIEURBURO " in standard_name)
    type_firm += bool(" INGENIEURGESELLSCHAFT " in standard_name)
    type_firm += bool(" INGENIEURSBUERO " in standard_name)
    type_firm += bool(" INGENIEURSBUREAU " in standard_name)
    type_firm += bool(" INGENIOERSBYRA " in standard_name)
    type_firm += bool(" INGENJOERSFIRMA " in standard_name)
    type_firm += bool(" INGENJOERSFIRMAN " in standard_name)
    type_firm += bool(" INORPORATED " in standard_name)
    type_firm += bool(" INT " in standard_name)
    type_firm += bool(" INT L " in standard_name)
    type_firm += bool(" INTERNAITONAL " in standard_name)
    type_firm += bool(" INTERNATIONAL " in standard_name)
    type_firm += bool(" INTERNATIONAL BUSINESS " in standard_name)
    type_firm += bool(" INTERNATIONALE " in standard_name)
    type_firm += bool(" INTERNATIONAUX " in standard_name)
    type_firm += bool(" INTERNTIONAL " in standard_name)
    type_firm += bool(" INTL " in standard_name)
    type_firm += bool(" INUDSTRIE " in standard_name)
    type_firm += bool(" INVESTMENT " in standard_name)
    type_firm += bool(" IS " in standard_name)
    type_firm += bool(" JOINTVENTURE " in standard_name)
    type_firm += bool(" K G " in standard_name)
    type_firm += bool(" K K " in standard_name)
    type_firm += bool(" KABAUSHIKI KAISHA " in standard_name)
    type_firm += bool(" KABISHIKI KAISHA " in standard_name)
    type_firm += bool(" KABSUHIKI " in standard_name)
    type_firm += bool(" KABUSHI KIKAISHA " in standard_name)
    type_firm += bool(" KABUSHIBI KAISHA " in standard_name)
    type_firm += bool(" KABUSHIKAISHA " in standard_name)
    type_firm += bool(" KABUSHIKI " in standard_name)
    type_firm += bool(" KABUSHIKKAISHA " in standard_name)
    type_firm += bool(" KABUSHIKU KASISHA " in standard_name)
    type_firm += bool(" KABUSHKIKI KAISHI " in standard_name)
    type_firm += bool(" KABUSIKI " in standard_name)
    type_firm += bool(" KABUSIKI KAISHA " in standard_name)
    type_firm += bool(" KABUSIKI KAISYA " in standard_name)
    type_firm += bool(" KABUSIKIKAISHA " in standard_name)
    type_firm += bool(" KAGUSHIKI KAISHA " in standard_name)
    type_firm += bool(" KAUSHIKI KAISHA " in standard_name)
    type_firm += bool(" KAISHA " in standard_name)
    type_firm += bool(" KAISYA " in standard_name)
    type_firm += bool(" KABAUSHIKI GAISHA " in standard_name)
    type_firm += bool(" KABISHIKI GAISHA " in standard_name)
    type_firm += bool(" KABUSHI KIGAISHA " in standard_name)
    type_firm += bool(" KABUSHIBI GAISHA " in standard_name)
    type_firm += bool(" KABUSHIGAISHA " in standard_name)
    type_firm += bool(" KABUSHIKGAISHA " in standard_name)
    type_firm += bool(" KABUSHIKU GASISHA " in standard_name)
    type_firm += bool(" KABUSHKIKI GAISHI " in standard_name)
    type_firm += bool(" KABUSIKI GAISHA " in standard_name)
    type_firm += bool(" KABUSIKI GAISYA " in standard_name)
    type_firm += bool(" KABUSIKIGAISHA " in standard_name)
    type_firm += bool(" KAGUSHIKI GAISHA " in standard_name)
    type_firm += bool(" KAUSHIKI GAISHA " in standard_name)
    type_firm += bool(" GAISHA " in standard_name)
    type_firm += bool(" GAISYA " in standard_name)
    type_firm += bool(" KB " in standard_name)
    type_firm += bool(" KB KY " in standard_name)
    type_firm += bool(" KFT " in standard_name)
    type_firm += bool(" KG " in standard_name)
    type_firm += bool(" KGAA " in standard_name)
    type_firm += bool(" KK " in standard_name)
    type_firm += bool(" KOM GES " in standard_name)
    type_firm += bool(" KOMM GES " in standard_name)
    type_firm += bool(" KOMMANDITBOLAG " in standard_name)
    type_firm += bool(" KOMMANDITBOLAGET " in standard_name)
    type_firm += bool(" KOMMANDITGESELLSCHAFT " in standard_name)
    type_firm += bool(" KONSTRUKTIONEN " in standard_name)
    type_firm += bool(" KOOPERATIVE " in standard_name)
    type_firm += bool(" KS " in standard_name)
    type_firm += bool(" KUBUSHIKI KAISHA " in standard_name)
    type_firm += bool(" KY " in standard_name)
    type_firm += bool(" L " in standard_name)
    type_firm += bool(" L C " in standard_name)
    type_firm += bool(" L L C " in standard_name)
    type_firm += bool(" L P " in standard_name)
    type_firm += bool(" LAB " in standard_name)
    type_firm += bool(" LABARATOIRE " in standard_name)
    type_firm += bool(" LABO " in standard_name)
    type_firm += bool(" LABORATOIRE " in standard_name)
    type_firm += bool(" LABORATOIRES " in standard_name)
    type_firm += bool(" LABORATORI " in standard_name)
    type_firm += bool(" LABORATORIA " in standard_name)
    type_firm += bool(" LABORATORIE " in standard_name)
    type_firm += bool(" LABORATORIES " in standard_name)
    type_firm += bool(" LABORATORIET " in standard_name)
    type_firm += bool(" LABORATORIUM " in standard_name)
    type_firm += bool(" LABORATORY " in standard_name)
    type_firm += bool(" LABRATIORIES " in standard_name)
    type_firm += bool(" LABS " in standard_name)
    type_firm += bool(" LC " in standard_name)
    type_firm += bool(" LCC " in standard_name)
    type_firm += bool(" LDA " in standard_name)
    type_firm += bool(" LDT " in standard_name)
    type_firm += bool(" LIIMITED " in standard_name)
    type_firm += bool(" LIMIDADA " in standard_name)
    type_firm += bool(" LIMINTED " in standard_name)
    type_firm += bool(" LIMITADA " in standard_name)
    type_firm += bool(" LIMITADO " in standard_name)
    type_firm += bool(" LIMITATA " in standard_name)
    type_firm += bool(" LIMITE " in standard_name)
    type_firm += bool(" LIMITED " in standard_name)
    type_firm += bool(" LIMITEE " in standard_name)
    type_firm += bool(" LIMTED " in standard_name)
    type_firm += bool(" LINITED " in standard_name)
    type_firm += bool(" LITD " in standard_name)
    type_firm += bool(" LLC " in standard_name)
    type_firm += bool(" LLLC " in standard_name)
    type_firm += bool(" LLLP " in standard_name)
    type_firm += bool(" LLP " in standard_name)
    type_firm += bool(" LMITED " in standard_name)
    type_firm += bool(" LP " in standard_name)
    type_firm += bool(" LT EE " in standard_name)
    type_firm += bool(" LTA " in standard_name)
    type_firm += bool(" LTC " in standard_name)
    type_firm += bool(" LTD " in standard_name)
    type_firm += bool(" LTD: " in standard_name)
    type_firm += bool(" LTDA " in standard_name)
    type_firm += bool(" LTDS " in standard_name)
    type_firm += bool(" LTEE " in standard_name)
    type_firm += bool(" LTEE; " in standard_name)
    type_firm += bool(" LTS " in standard_name)
    type_firm += bool(" MAATSCHAPPIJ " in standard_name)
    type_firm += bool(" MANUFACTURE " in standard_name)
    type_firm += bool(" MANUFACTURE D ARTICLES " in standard_name)
    type_firm += bool(" MANUFACTURE DE " in standard_name)
    type_firm += bool(" MANUFACTURING " in standard_name)
    type_firm += bool(" MARKETING " in standard_name)
    type_firm += bool(" MASCHINENBAU " in standard_name)
    type_firm += bool(" MASCHINENFABRIK " in standard_name)
    type_firm += bool(" MBH " in standard_name)
    type_firm += bool(" MBH & CO " in standard_name)
    type_firm += bool(" MERCHANDISING " in standard_name)
    type_firm += bool(" MET BEPERKTE " in standard_name)
    type_firm += bool(" MFG " in standard_name)
    type_firm += bool(" N A " in standard_name)
    type_firm += bool(" N V " in standard_name)
    type_firm += bool(" NA " in standard_name)
    type_firm += bool(" NAAMLOSE " in standard_name)
    type_firm += bool(" NAAMLOZE " in standard_name)
    type_firm += bool(" NAAMLOZE VENNOOTSCAP " in standard_name)
    type_firm += bool(" NAAMLOZE VENNOOTSHCAP " in standard_name)
    type_firm += bool(" NAAMLOZEVENNOOTSCHAP " in standard_name)
    type_firm += bool(" NAUCHNO PRIOZVODSTVENNAYA FIRMA " in standard_name)
    type_firm += bool(" NAUCHNO PRIOZVODSTVENNOE OBIEDINENIE " in standard_name)
    type_firm += bool(" NAUCHNO PRIOZVODSTVENNY KOOPERATIV " in standard_name)
    type_firm += bool(" NAUCHNO PROIZVODSTVENNOE " in standard_name)
    type_firm += bool(" NAUCHNO PROIZVODSTVENNOE OBJEDINENIE " in standard_name)
    type_firm += bool(" NAUCHNO TEKHNICHESKY KOOPERATIV " in standard_name)
    type_firm += bool(" NAUCHNO TEKHNICHESKYKKOOPERATIV " in standard_name)
    type_firm += bool(" NAUCHNO TEKHNOLOGICHESKOE " in standard_name)
    type_firm += bool(" NAUCHNO TEKHNOLOGICHESKOEPREDPRIYATIE " in standard_name)
    type_firm += bool(" NAUCHNOPRIOZVODSTVENNOE " in standard_name)
    type_firm += bool(" NAUCHNOPROIZVODSTVENNOE " in standard_name)
    type_firm += bool(" NAUCHNOTEKHNICHESKYKKOOPERATIV " in standard_name)
    type_firm += bool(" NAUCHNOTEKNICHESKY " in standard_name)
    type_firm += bool(" NV " in standard_name)
    type_firm += bool(" NV SA " in standard_name)
    type_firm += bool(" NV: " in standard_name)
    type_firm += bool(" NVSA " in standard_name)
    type_firm += bool(" OBIDINENIE " in standard_name)
    type_firm += bool(" OBIED " in standard_name)
    type_firm += bool(" OBSCHESRYO " in standard_name)
    type_firm += bool(" OBSCHESTVO & OGRANICHENNOI OTVETSTVENNOSTJU " in standard_name)
    type_firm += bool(" OBSCHESTVO & ORGANICHENNOI OTVETSTVENNOSTIJU " in standard_name)
    type_firm += bool(" OBSCHESTVO C " in standard_name)
    type_firm += bool(" OBSCHESTVO S " in standard_name)
    type_firm += bool(" OBSCHESTVO S OGRANICHENNOI " in standard_name)
    type_firm += bool(" OBSCHESTVO S OGRANICHENNOI OTVETSTVEN NOSTJU " in standard_name)
    type_firm += bool(" OBSCHESTVO S OGRANICHENNOI OTVETSTVENNOSTIJU " in standard_name)
    type_firm += bool(" OBSCHESTVO S OGRANICHENNOI OTVETSTVENNPSTJU " in standard_name)
    type_firm += bool(" OBSCHESTVO S OGRANICHENNOY OTVETSTVENNOSTJU " in standard_name)
    type_firm += bool(" OBSCHESTVO S OGRANICHENOI " in standard_name)
    type_firm += bool(" OBSCHESTVO S ORGANICHENNOI OTVETSTVENNOSTIJU " in standard_name)
    type_firm += bool(" OBSCHESTVO S ORGANICHENNOI OTVETSTVENNOSTJU " in standard_name)
    type_firm += bool(" OBSHESTVO S " in standard_name)
    type_firm += bool(" OBSHESTVO S OGRANNICHENNOJ " in standard_name)
    type_firm += bool(" OBSHESTVO S ORGANICHENNOI OTVETSTVENNOSTIJU " in standard_name)
    type_firm += bool(" OBSHESTVO S ORGANICHENNOI OTVETSTVENNOSTJU " in standard_name)
    type_firm += bool(" OCTROOIBUREAU " in standard_name)
    type_firm += bool(" OGRANICHENNOI OTVETSTVENNOSTIJU " in standard_name)
    type_firm += bool(" OGRANICHENNOI OTVETSTVENNOSTIJU FIRMA " in standard_name)
    type_firm += bool(" OGRANICHENNOI OTVETSTVENNOSTJU " in standard_name)
    type_firm += bool(" OGRANICHENNOY OTVETSTVENNOSTYU " in standard_name)
    type_firm += bool(" OHG " in standard_name)
    type_firm += bool(" ONDERNEMING " in standard_name)
    type_firm += bool(" OTVETCTVENNOSTJU " in standard_name)
    type_firm += bool(" OTVETSTVENNOSTIJU " in standard_name)
    type_firm += bool(" OTVETSTVENNOSTJU " in standard_name)
    type_firm += bool(" OTVETSTVENNOSTOU " in standard_name)
    type_firm += bool(" OTVETSTVENNOSTYU " in standard_name)
    type_firm += bool(" OY " in standard_name)
    type_firm += bool(" OYABLTD " in standard_name)
    type_firm += bool(" OYG " in standard_name)
    type_firm += bool(" OYI " in standard_name)
    type_firm += bool(" OYJ " in standard_name)
    type_firm += bool(" OYL " in standard_name)
    type_firm += bool(" P " in standard_name)
    type_firm += bool(" P C " in standard_name)
    type_firm += bool(" P L C " in standard_name)
    type_firm += bool(" PARNERSHIP " in standard_name)
    type_firm += bool(" PARNTERSHIP " in standard_name)
    type_firm += bool(" PARTNER " in standard_name)
    type_firm += bool(" PARTNERS " in standard_name)
    type_firm += bool(" PARTNERSHIP " in standard_name)
    type_firm += bool(" PATENT OFFICE " in standard_name)
    type_firm += bool(" PATENTVERWALTUNGS GESELLSCHAFT MBH " in standard_name)
    type_firm += bool(" PATENTVERWALTUNGSGESELLSCHAFT " in standard_name)
    type_firm += bool(" PATENTVERWERTUNGSGESELLSCHAFT " in standard_name)
    type_firm += bool(" PATNERSHIP " in standard_name)
    type_firm += bool(" PC " in standard_name)
    type_firm += bool(" PER AZIONA " in standard_name)
    type_firm += bool(" PERSONENVENNOOTSCHAP MET BE PERKTE AANSPRAKELIJKHEID " in standard_name)
    type_firm += bool(" PHARM " in standard_name)
    type_firm += bool(" PHARMACEUTICA " in standard_name)
    type_firm += bool(" PHARMACEUTICAL " in standard_name)
    type_firm += bool(" PHARMACEUTICALS " in standard_name)
    type_firm += bool(" PHARMACEUTIQUE " in standard_name)
    type_firm += bool(" PHARMACIA " in standard_name)
    type_firm += bool(" PHARMACIE " in standard_name)
    type_firm += bool(" PHARMACUETICALS " in standard_name)
    type_firm += bool(" PLANTS " in standard_name)
    type_firm += bool(" PLC " in standard_name)
    type_firm += bool(" PREDPRIVATIE " in standard_name)
    type_firm += bool(" PREDPRIYATIE " in standard_name)
    type_firm += bool(" PREPRIVATIE " in standard_name)
    type_firm += bool(" PRODUCE " in standard_name)
    type_firm += bool(" PRODUCT " in standard_name)
    type_firm += bool(" PRODUCTEURS " in standard_name)
    type_firm += bool(" PRODUCTION " in standard_name)
    type_firm += bool(" PRODUCTIONS " in standard_name)
    type_firm += bool(" PRODUCTIQUE " in standard_name)
    type_firm += bool(" PRODUCTS " in standard_name)
    type_firm += bool(" PRODUITS " in standard_name)
    type_firm += bool(" PRODUKTE " in standard_name)
    type_firm += bool(" PRODUKTER " in standard_name)
    type_firm += bool(" PRODUKTION " in standard_name)
    type_firm += bool(" PRODUKTIONSGESELLSCHAFT " in standard_name)
    type_firm += bool(" PRODUKTUTVECKLING " in standard_name)
    type_firm += bool(" PRODURA " in standard_name)
    type_firm += bool(" PRODUTIS " in standard_name)
    type_firm += bool(" PROIZVODSTENNOE OBIEDINENIE " in standard_name)
    type_firm += bool(" PROIZVODSTVENNOE " in standard_name)
    type_firm += bool(" PROIZVODSTVENNOE OBIEDINENIE " in standard_name)
    type_firm += bool(" PTY " in standard_name)
    type_firm += bool(" PTY LIM " in standard_name)
    type_firm += bool(" PTYLTD " in standard_name)
    type_firm += bool(" PUBLISHING " in standard_name)
    type_firm += bool(" PVBA " in standard_name)
    type_firm += bool(" RECHERCHES " in standard_name)
    type_firm += bool(" RESPONSABILITA LIMITATA " in standard_name)
    type_firm += bool(" RESPONSABILITA� LIMITATA " in standard_name)
    type_firm += bool(" RESPONSABILITE LIMITE " in standard_name)
    type_firm += bool(" RO " in standard_name)
    type_firm += bool(" RT " in standard_name)
    type_firm += bool(" S A " in standard_name)
    type_firm += bool(" S A R L " in standard_name)
    type_firm += bool(" S A RL " in standard_name)
    type_firm += bool(" S COOP " in standard_name)
    type_firm += bool(" S COOP LTDA " in standard_name)
    type_firm += bool(" S NC " in standard_name)
    type_firm += bool(" S OGRANICHENNOI OTVETSTVENNEST " in standard_name)
    type_firm += bool(" S P A " in standard_name)
    type_firm += bool(" S PA " in standard_name)
    type_firm += bool(" S R L " in standard_name)
    type_firm += bool(" S RL " in standard_name)
    type_firm += bool(" S S " in standard_name)
    type_firm += bool(" SA " in standard_name)
    type_firm += bool(" SA A RL " in standard_name)
    type_firm += bool(" SA RL " in standard_name)
    type_firm += bool(" SA: " in standard_name)
    type_firm += bool(" SAAG " in standard_name)
    type_firm += bool(" SAARL " in standard_name)
    type_firm += bool(" SALES " in standard_name)
    type_firm += bool(" SANV " in standard_name)
    type_firm += bool(" SARL " in standard_name)
    type_firm += bool(" SARL: " in standard_name)
    type_firm += bool(" SAS " in standard_name)
    type_firm += bool(" SC " in standard_name)
    type_firm += bool(" SCA " in standard_name)
    type_firm += bool(" SCARL " in standard_name)
    type_firm += bool(" SCIETE ANONYME " in standard_name)
    type_firm += bool(" SCOOP " in standard_name)
    type_firm += bool(" SCPA " in standard_name)
    type_firm += bool(" SCRAS " in standard_name)
    type_firm += bool(" SCRL " in standard_name)
    type_firm += bool(" SEMPLICE " in standard_name)
    type_firm += bool(" SERIVICES " in standard_name)
    type_firm += bool(" SERVICE " in standard_name)
    type_firm += bool(" SERVICES " in standard_name)
    type_firm += bool(" SHOP " in standard_name)
    type_firm += bool(" SIMPLIFIEE " in standard_name)
    type_firm += bool(" SL " in standard_name)
    type_firm += bool(" SNC " in standard_name)
    type_firm += bool(" SOC " in standard_name)
    type_firm += bool(" SOC ARL " in standard_name)
    type_firm += bool(" SOC COOOP ARL " in standard_name)
    type_firm += bool(" SOC COOP A RESP LIM " in standard_name)
    type_firm += bool(" SOC COOP A RL " in standard_name)
    type_firm += bool(" SOC COOP R L " in standard_name)
    type_firm += bool(" SOC COOP RL " in standard_name)
    type_firm += bool(" SOC IND COMM " in standard_name)
    type_firm += bool(" SOC RL " in standard_name)
    type_firm += bool(" SOCCOOP ARL " in standard_name)
    type_firm += bool(" SOCCOOPARL " in standard_name)
    type_firm += bool(" SOCIEDAD " in standard_name)
    type_firm += bool(" SOCIEDAD ANONIMA " in standard_name)
    type_firm += bool(" SOCIEDAD ANONIMYA " in standard_name)
    type_firm += bool(" SOCIEDAD INDUSTRIAL " in standard_name)
    type_firm += bool(" SOCIEDAD LIMITADA " in standard_name)
    type_firm += bool(" SOCIEDADE LIMITADA " in standard_name)
    type_firm += bool(" SOCIET CIVILE " in standard_name)
    type_firm += bool(" SOCIETA " in standard_name)
    type_firm += bool(" SOCIETA A " in standard_name)
    type_firm += bool(" SOCIETA A RESPONSABILITA LIMITATA " in standard_name)
    type_firm += bool(" SOCIETA ANONIMA " in standard_name)
    type_firm += bool(" SOCIETA CONSORTILE " in standard_name)
    type_firm += bool(" SOCIETA CONSORTILE A RESPONSABILITA " in standard_name)
    type_firm += bool(" SOCIETA CONSORTILE ARL " in standard_name)
    type_firm += bool(" SOCIETA CONSORTILE PER AZION " in standard_name)
    type_firm += bool(" SOCIETA CONSORTILE PER AZIONI " in standard_name)
    type_firm += bool(" SOCIETA COOPERATIVA " in standard_name)
    type_firm += bool(" SOCIETA COOPERATIVA A " in standard_name)
    type_firm += bool(" SOCIETA IN ACCOMANDITA " in standard_name)
    type_firm += bool(" SOCIETA IN ACCOMANDITA SEMPLICE " in standard_name)
    type_firm += bool(" SOCIETA IN NOME COLLETTIVO " in standard_name)
    type_firm += bool(" SOCIETA INDUSTRIA " in standard_name)
    type_firm += bool(" SOCIETA PER AXIONI " in standard_name)
    type_firm += bool(" SOCIETA PER AZINOI " in standard_name)
    type_firm += bool(" SOCIETA PER AZINONI " in standard_name)
    type_firm += bool(" SOCIETA PER AZIONI " in standard_name)
    type_firm += bool(" SOCIETA PER AZIONI: " in standard_name)
    type_firm += bool(" SOCIETA PER L INDUSTRIA " in standard_name)
    type_firm += bool(" SOCIETA PERAZIONI " in standard_name)
    type_firm += bool(" SOCIETAPERAZIONI " in standard_name)
    type_firm += bool(" SOCIETE " in standard_name)
    type_firm += bool(" SOCIETE A " in standard_name)
    type_firm += bool(" SOCIETE A RESPONSABILITE " in standard_name)
    type_firm += bool(" SOCIETE A RESPONSABILITE DITE " in standard_name)
    type_firm += bool(" SOCIETE A RESPONSABILITEE " in standard_name)
    type_firm += bool(" SOCIETE ANANYME " in standard_name)
    type_firm += bool(" SOCIETE ANNOYME " in standard_name)
    type_firm += bool(" SOCIETE ANOMYME " in standard_name)
    type_firm += bool(" SOCIETE ANOMYNE " in standard_name)
    type_firm += bool(" SOCIETE ANONVME " in standard_name)
    type_firm += bool(" SOCIETE ANONYM " in standard_name)
    type_firm += bool(" SOCIETE ANONYME " in standard_name)
    type_firm += bool(" SOCIETE ANOYME " in standard_name)
    type_firm += bool(" SOCIETE CHIMIQUE " in standard_name)
    type_firm += bool(" SOCIETE CIVILE " in standard_name)
    type_firm += bool(" SOCIETE COOPERATIVE " in standard_name)
    type_firm += bool(" SOCIETE D APPLICATIONS GENERALES " in standard_name)
    type_firm += bool(" SOCIETE D APPLICATIONS MECANIQUES " in standard_name)
    type_firm += bool(" SOCIETE D EQUIPEMENT " in standard_name)
    type_firm += bool(" SOCIETE D ETUDE ET DE CONSTRUCTION " in standard_name)
    type_firm += bool(" SOCIETE D ETUDE ET DE RECHERCHE EN VENTILATION " in standard_name)
    type_firm += bool(" SOCIETE D ETUDES ET " in standard_name)
    type_firm += bool(" SOCIETE D ETUDES TECHNIQUES ET D ENTREPRISES " in standard_name)
    type_firm += bool(" SOCIETE DE " in standard_name)
    type_firm += bool(" SOCIETE DE CONSEILS DE RECHERCHES ET D APPLICATIONS " in standard_name)
    type_firm += bool(" SOCIETE DE CONSTRUCTIO " in standard_name)
    type_firm += bool(" SOCIETE DE FABRICAITON " in standard_name)
    type_firm += bool(" SOCIETE DE FABRICATION " in standard_name)
    type_firm += bool(" SOCIETE DE PRODUCTION ET DE " in standard_name)
    type_firm += bool(" SOCIETE DES TRANSPORTS " in standard_name)
    type_firm += bool(" SOCIETE DITE " in standard_name)
    type_firm += bool(" SOCIETE DITE : " in standard_name)
    type_firm += bool(" SOCIETE DITE: " in standard_name)
    type_firm += bool(" SOCIETE EN " in standard_name)
    type_firm += bool(" SOCIETE EN COMMANDITE " in standard_name)
    type_firm += bool(" SOCIETE EN COMMANDITE ENREGISTREE " in standard_name)
    type_firm += bool(" SOCIETE EN NOM COLLECTIF " in standard_name)
    type_firm += bool(" SOCIETE ETUDES ET " in standard_name)
    type_firm += bool(" SOCIETE ETUDES ET DEVELOPPEMENTS " in standard_name)
    type_firm += bool(" SOCIETE GENERALE POUR LES " in standard_name)
    type_firm += bool(" SOCIETE GENERALE POUR LES TECHNIQUES NOVELLES " in standard_name)
    type_firm += bool(" SOCIETE METALLURGIQUE " in standard_name)
    type_firm += bool(" SOCIETE NOUVELLE " in standard_name)
    type_firm += bool(" SOCIETE PAR ACTIONS " in standard_name)
    type_firm += bool(" SOCIETE PAR ACTIONS SIMPLIFEE " in standard_name)
    type_firm += bool(" SOCIETE PAR ACTIONS SIMPLIFIEE " in standard_name)
    type_firm += bool(" SOCIETE TECHNIQUE D APPLICATION ET DE RECHERCHE " in standard_name)
    type_firm += bool(" SOCIETE TECHNIQUE DE PULVERISATION " in standard_name)
    type_firm += bool(" SOCIETEANONYME " in standard_name)
    type_firm += bool(" SOCIETEDITE " in standard_name)
    type_firm += bool(" SOCIETEINDUSTRIELLE " in standard_name)
    type_firm += bool(" SOCRL " in standard_name)
    type_firm += bool(" SOEHNE " in standard_name)
    type_firm += bool(" SOGRANICHENNOI OTVETSTVENNOSTJU " in standard_name)
    type_firm += bool(" SOHN " in standard_name)
    type_firm += bool(" SOHNE " in standard_name)
    type_firm += bool(" SONNER " in standard_name)
    type_firm += bool(" SP " in standard_name)
    type_firm += bool(" SP A " in standard_name)
    type_firm += bool(" SP Z OO " in standard_name)
    type_firm += bool(" SP ZOO " in standard_name)
    type_firm += bool(" SPA " in standard_name)
    type_firm += bool(" SPOKAZOO " in standard_name)
    type_firm += bool(" SPOL " in standard_name)
    type_firm += bool(" SPOL S R O " in standard_name)
    type_firm += bool(" SPOL S RO " in standard_name)
    type_firm += bool(" SPOL SRO " in standard_name)
    type_firm += bool(" SPOLECNOST SRO " in standard_name)
    type_firm += bool(" SPOLKA Z OO " in standard_name)
    type_firm += bool(" SPOLKA ZOO " in standard_name)
    type_firm += bool(" SPOLS RO " in standard_name)
    type_firm += bool(" SPOLSRO " in standard_name)
    type_firm += bool(" SPRL " in standard_name)
    type_firm += bool(" SPZ OO " in standard_name)
    type_firm += bool(" SPZOO " in standard_name)
    type_firm += bool(" SR " in standard_name)
    type_firm += bool(" SR L " in standard_name)
    type_firm += bool(" SR1 " in standard_name)
    type_firm += bool(" SRI " in standard_name)
    type_firm += bool(" SRL " in standard_name)
    type_firm += bool(" SRO " in standard_name)
    type_firm += bool(" S�RL " in standard_name)
    type_firm += bool(" SURL " in standard_name)
    type_firm += bool(" TEAM " in standard_name)
    type_firm += bool(" TECHNIQUES NOUVELLE " in standard_name)
    type_firm += bool(" TECHNOLOGIES " in standard_name)
    type_firm += bool(" THE FIRM " in standard_name)
    type_firm += bool(" TOHO BUSINESS " in standard_name)
    type_firm += bool(" TOVARISCHESIVO S OGRANICHENNOI OIVETSIVENNOSTIJU " in standard_name)
    type_firm += bool(" TOVARISCHESTVO " in standard_name)
    type_firm += bool(" TOVARISCHESTVO S OGRANICHENNOI " in standard_name)
    type_firm += bool(" TOVARISCHESTVO S OGRANICHENNOI OTVETSTVENNOSTJU " in standard_name)
    type_firm += bool(" TOVARISCHESTVO S OGRANICHENNOI OTVETSVENNOSTJU " in standard_name)
    type_firm += bool(" TOVARISCHESTVO S ORGANICHENNOI OTVETSTVENNOSTJU " in standard_name)
    type_firm += bool(" TOVARISCHETSTVO S ORGANICHENNOI " in standard_name)
    type_firm += bool(" TRADING " in standard_name)
    type_firm += bool(" TRADING AS " in standard_name)
    type_firm += bool(" TRADING UNDER " in standard_name)
    type_firm += bool(" UGINE " in standard_name)
    type_firm += bool(" UNTERNEHMEN " in standard_name)
    type_firm += bool(" USA " in standard_name)
    type_firm += bool(" USINES " in standard_name)
    type_firm += bool(" VAKMANSCHAP " in standard_name)
    type_firm += bool(" VENNOOTSCHAP " in standard_name)
    type_firm += bool(" VENNOOTSCHAP ONDER FIRMA: " in standard_name)
    type_firm += bool(" VENNOOTSHAP " in standard_name)
    type_firm += bool(" VENNOTSCHAP " in standard_name)
    type_firm += bool(" VENOOTSCHAP " in standard_name)
    type_firm += bool(" VENTURE " in standard_name)
    type_firm += bool(" VERARBEITUNG " in standard_name)
    type_firm += bool(" VERKOOP " in standard_name)
    type_firm += bool(" VERSICHERUNGSBUERO " in standard_name)
    type_firm += bool(" VERTRIEBSGESELLSCHAFT " in standard_name)
    type_firm += bool(" VOF " in standard_name)
    type_firm += bool(" WERK " in standard_name)
    type_firm += bool(" WERKE " in standard_name)
    type_firm += bool(" WERKEN " in standard_name)
    type_firm += bool(" WERKHUIZEN " in standard_name)
    type_firm += bool(" WERKS " in standard_name)
    type_firm += bool(" WERKSTAETTE " in standard_name)
    type_firm += bool(" WERKSTATT " in standard_name)
    type_firm += bool(" WERKZEUGBAU " in standard_name)
    type_firm += bool(" WINKEL " in standard_name)
    type_firm += bool(" WORKS " in standard_name)
    type_firm += bool(" YUGEN KAISHA " in standard_name)
    type_firm += bool(" YUGENKAISHA " in standard_name)
    type_firm += bool(" YUUGEN KAISHA " in standard_name)
    type_firm += bool(" YUUGENKAISHA " in standard_name)
    type_firm += bool(" ZOO " in standard_name)

    return((type_firm>0))

# %%
##############################################################
# PROCEDURE 3b Combine single char sequences                 #
##############################################################

def combabbrev(standard_name):
    # =============================================================================
    # * combabbrev.do
    #
    # * 1/2007 JBessen
    # *
    # * combine single char sequences in standard_name
    # * this assumes name string begins and ends with space
    # =============================================================================

    outname = " "

    # remove quote characters
    standard_name = standard_name.replace("\"",  "", 30)

    split_string = standard_name.split(' ')

    for n in range(len(split_string)):
        local_outname = split_string[n]
        if (len(split_string[n])!=1):
            local_outname = local_outname + ' '
        else:
            if (n!=(len(split_string)-1)):
                if (len(split_string[n+1])!=1):
                    local_outname = local_outname + ' '

        outname = outname + local_outname

    return(outname)


# %%
#############################################
# Procedure 4 CREATE STEM NAME              #
#############################################
def stem_name(stem_name):
    # =============================================================================
    # ************************************************************************************************
    # ** Procedure 4 CREATE STEM NAME
    # **
    # ** This section creates a name with all legal entity identifiers removed
    # **
    # ** Much of this problem (below) can be fixed by keeping the words separate. I am rewriting so
    # ** that the name begins and ends with a space - in this way, all changes of this kind can be
    # ** done by word. If you want to collapse the words for matching, it is best to do it at the end
    # ** of the cleaning.  BHH   Augsut 2006
    # **
    # ** This is rather crude, and can create problems. For example a firm called
    # ** "WINTER COATING LTD" would be changed to "WINTER ATING ", but it is only used as
    # ** a second match, after the standard name match, and the standard name is always retained.
    # ** Because of this problem, not all identifier types are removed, for example for Sweden we only
    # ** remove the AB idenitier, as it is by far the most common.
    # ************************************************************************************************
    # *cap prog drop stem_name
    # *prog def stem_name
    #
    # gen stem_name = standard_name
    # =============================================================================

    # Onw constribution, first stip leading and trailing white space and translate to lower
    # Then add white space around string to match description, needed for working with the strings
    stem_name = ' '+stem_name.upper().strip()+' '

    # UNITED KINGDOM
    for c in [" LTD ", " CO LTD ", " TRADING LTD ", " HLDGS ", " CORP ",
              " INTL ", " INC ", " PLC ", " SPA ", " CLA ", " LLP ",
              " LLC ", " AIS ", " INVESTMENTS ", " PARTNERSHIP ",
              " & CO ", " CO ", " COS ", " CP ", " LP ", " BLSA ", " GROUP "]:
        if c in stem_name:
            stem_name = stem_name.replace(c, " ", 1)


    # => ignore here the international context, so don't stem based on foreign names
    r'''
    # FRANCE
    stem_name = stem_name.replace(" SA ", " ", 1)
    stem_name = stem_name.replace(" SARL ", " ", 1)
    stem_name = stem_name.replace(" SAS ", " ", 1)
    stem_name = stem_name.replace(" EURL ", " ", 1)
    stem_name = stem_name.replace(" ETCIE ", " ", 1)
    stem_name = stem_name.replace(" ET CIE ", " ", 1)
    stem_name = stem_name.replace(" CIE ", " ", 1)
    stem_name = stem_name.replace(" GIE ", " ", 1)
    stem_name = stem_name.replace(" SC ", " ", 1)
    stem_name = stem_name.replace(" SNC ", " ", 1)
    stem_name = stem_name.replace(" SP ", " ", 1)
    stem_name = stem_name.replace(" SCS ", " ", 1)

    # GERMANY
    stem_name = stem_name.replace(" GMBHCOKG ", " ", 1)
    stem_name = stem_name.replace(" EGENOSSENSCHAFT ", " ", 1)
    stem_name = stem_name.replace(" GMBHCO ", " ", 1)
    stem_name = stem_name.replace(" COGMBH ", " ", 1)
    stem_name = stem_name.replace(" GESMBH ", " ", 1)
    stem_name = stem_name.replace(" GMBH ", " ", 1)
    stem_name = stem_name.replace(" KGAA ", " ", 1)
    stem_name = stem_name.replace(" KG ", " ", 1)
    stem_name = stem_name.replace(" AG ", " ", 1)
    stem_name = stem_name.replace(" EG ", " ", 1)
    stem_name = stem_name.replace(" GMBHCOKGAA ", " ", 1)
    stem_name = stem_name.replace(" MIT ", " ", 1)
    stem_name = stem_name.replace(" OHG ", " ", 1)
    stem_name = stem_name.replace(" GRUPPE ", " ", 1)
    stem_name = stem_name.replace(" GBR ", " ", 1)

    # Spain
    stem_name = stem_name.replace(" SL ", " ", 1)
    stem_name = stem_name.replace(" SA ", " ", 1)
    stem_name = stem_name.replace(" SC ", " ", 1)
    stem_name = stem_name.replace(" SRL ", " ", 1)
    stem_name = stem_name.replace(" ESPANA ", " ", 1)

    # Italy
    stem_name = stem_name.replace(" SA ", " ", 1)
    stem_name = stem_name.replace(" SAS ", " ", 1)
    stem_name = stem_name.replace(" SNC ", " ", 1)
    stem_name = stem_name.replace(" SPA ", " ", 1)
    stem_name = stem_name.replace(" SRL ", " ", 1)

    # SWEDEN - front and back
    stem_name = stem_name.replace(" AB ", " ", 1)
    stem_name = stem_name.replace(" HB ", " ", 1)
    stem_name = stem_name.replace(" KB ", " ", 1)

    # Belgium
    # Note: the belgians use a lot of French endings, so we include all the French ones.
    # Also, they use NV (belgian) and SA (french) interchangably, so standardise to SA

    #French ones again
    stem_name = stem_name.replace(" SAS ", " ", 1)
    stem_name = stem_name.replace(" SA ", " ", 1)
    stem_name = stem_name.replace(" SARL ", " ", 1)
    stem_name = stem_name.replace(" SARLU ", " ", 1)
    stem_name = stem_name.replace(" SAS ", " ", 1)
    stem_name = stem_name.replace(" SASU ", " ", 1)
    stem_name = stem_name.replace(" EURL ", " ", 1)
    stem_name = stem_name.replace(" ETCIE ", " ", 1)
    stem_name = stem_name.replace(" CIE ", " ", 1)
    stem_name = stem_name.replace(" GIE ", " ", 1)
    stem_name = stem_name.replace(" SC ", " ", 1)
    stem_name = stem_name.replace(" SNC ", " ", 1)
    stem_name = stem_name.replace(" SP ", " ", 1)
    stem_name = stem_name.replace(" SCS ", " ", 1)

    #Specifically Belgian ones
    stem_name = stem_name.replace(" BV ", " ", 1)
    stem_name = stem_name.replace(" CVA ", " ", 1)
    stem_name = stem_name.replace(" SCA ", " ", 1)
    stem_name = stem_name.replace(" SPRL ", " ", 1)

    #Change to French language equivalents where appropriate
    stem_name = stem_name.replace(" SCS ", " ", 1)
    stem_name = stem_name.replace(" SA ", " ", 1)
    stem_name = stem_name.replace(" SPRL ", " ", 1)

    # Denmark - front and back
    #Usually danish identifiers have a slash (eg. A/S or K/S), but these will have been removed with all
    #other punctuation earlier (so just use AS or KS).
    stem_name = stem_name.replace(" AMBA ", " ", 1)
    stem_name = stem_name.replace(" APS ", " ", 1)
    stem_name = stem_name.replace(" AS ", " ", 1)
    stem_name = stem_name.replace(" IS ", " ", 1)
    stem_name = stem_name.replace(" KAS ", " ", 1)
    stem_name = stem_name.replace(" KS ", " ", 1)
    stem_name = stem_name.replace(" PF ", " ", 1)

    # Norway - front and back
    stem_name = stem_name.replace(" AL ", " ", 1)
    stem_name = stem_name.replace(" ANS ", " ", 1)
    stem_name = stem_name.replace(" AS ", " ", 1)
    stem_name = stem_name.replace(" ASA ", " ", 1)
    stem_name = stem_name.replace(" DA ", " ", 1)
    stem_name = stem_name.replace(" KS ", " ", 1)

    # Netherlands - front and back
    stem_name = stem_name.replace(" BV ", " ", 1)
    stem_name = stem_name.replace(" CV ", " ", 1)
    stem_name = stem_name.replace(" CVOA ", " ", 1)
    stem_name = stem_name.replace(" NV ", " ", 1)
    stem_name = stem_name.replace(" VOF ", " ", 1)

    # Finland - front and back
    # We get some LTD and PLC strings for finland. Remove.
    stem_name = stem_name.replace(" AB ", " ", 1)
    stem_name = stem_name.replace(" APB ", " ", 1)
    stem_name = stem_name.replace(" KB ", " ", 1)
    stem_name = stem_name.replace(" KY ", " ", 1)
    stem_name = stem_name.replace(" OY ", " ", 1)
    stem_name = stem_name.replace(" OYJ ", " ", 1)
    stem_name = stem_name.replace(" OYJ AB ", " ", 1)
    stem_name = stem_name.replace(" OY AB ", " ", 1)
    stem_name = stem_name.replace(" LTD ", " ", 1)
    stem_name = stem_name.replace(" PLC ", " ", 1)
    stem_name = stem_name.replace(" INC ", " ", 1)

    # Poland
    stem_name = stem_name.replace(" SA ", " ", 1)
    stem_name = stem_name.replace(" SC ", " ", 1)
    stem_name = stem_name.replace(" SK ", " ", 1)
    stem_name = stem_name.replace(" SPZOO ", " ", 1)

    # Greece
    # Also see limited and so on sometimes
    stem_name = stem_name.replace(" AE ", " ", 1)
    stem_name = stem_name.replace(" EE ", " ", 1)
    stem_name = stem_name.replace(" EPE ", " ", 1)
    stem_name = stem_name.replace(" OE ", " ", 1)
    stem_name = stem_name.replace(" SA ", " ", 1)
    stem_name = stem_name.replace(" LTD ", " ", 1)
    stem_name = stem_name.replace(" PLC ", " ", 1)
    stem_name = stem_name.replace(" INC ", " ", 1)

    # Czech Republic
    stem_name = stem_name.replace(" AS ", " ", 1)
    stem_name = stem_name.replace(" KS ", " ", 1)
    stem_name = stem_name.replace(" SRO ", " ", 1)
    stem_name = stem_name.replace(" VOS ", " ", 1)

    # Bulgaria
    stem_name = stem_name.replace(" AD ", " ", 1)
    stem_name = stem_name.replace(" KD ", " ", 1)
    stem_name = stem_name.replace(" KDA ", " ", 1)
    stem_name = stem_name.replace(" OCD ", " ", 1)
    stem_name = stem_name.replace(" KOOP ", " ", 1)
    stem_name = stem_name.replace(" DF ", " ", 1)
    stem_name = stem_name.replace(" EOOD ", " ", 1)
    stem_name = stem_name.replace(" EAD ", " ", 1)
    stem_name = stem_name.replace(" OOD ", " ", 1)
    stem_name = stem_name.replace(" KOOD ", " ", 1)
    stem_name = stem_name.replace(" ET ", " ", 1)

    # Japan
    stem_name = stem_name.replace(" KOGYO KK ", " ", 1)
    stem_name = stem_name.replace(" KK ", " ", 1)
    r'''

    stem_name = stem_name.replace("  ", " ", 30)
    #stem_name = re.sub("  "," ", stem_name, 30)
    return(stem_name.strip())

# %%
######################################################
# Manual Name adjustment for certain patent IDs      #
######################################################
def manual_patent_name_cleaning(patent_id):
    '''returns manually matched standard_names to patent id'''
    # Source: Pian Shu, paper https://www.aeaweb.org/articles?id=10.1257/aeri.20180481
    patent = str(patent_id)
    if len(patent)<8: patent = '0'+patent
    
    if patent=="04763358": standard_name= " INTERSONICS INCORPORATED LEGRAPH COMPANY " 
    if patent=="06726949": standard_name= " CONOPCO INC "
    if patent=="07433412": standard_name= " ATT INTELLECTUAL PROPERTY LLP "
    if patent=="08129369": standard_name= " COUNCIL OF SCIENTIFIC & INDUSTRIAL RESEARCH " 
    if  patent=="07755899": standard_name=" AAC MICROTEC AB " 
    if  patent=="03942650": standard_name=" VALLOUREC " 
    if  patent=="04063430": standard_name=" CG DORIS " 
    if  patent=="04496975": standard_name=" LETAT FRANCAIS REPRESENTE PAR LE MINISTRE DES PA " 
    if  patent=="04612551": standard_name=" SCR " 
    if  patent=="04911848": standard_name=" ERAMET SLN " 
    if  patent=="05257922": standard_name=" SOLVAY & CIE "
    if  patent=="05339992": standard_name=" SOCIETE DE PROSPECTION ET DINVENTIONS TECHNIQUES " 
    if  patent=="05377198": standard_name=" NCR CORPORATION " 
    if  patent=="05464599": standard_name=" SOLVAY " 
    if  patent=="05537290": standard_name=" TEKNION FURNITURE SYSTEMS " 
    if  patent=="06264523": standard_name=" TRI STATE CORPORATION " 
    if  patent=="06499943": standard_name=" ALSTOM LTD " 
    if  patent=="06742772": standard_name=" ATLANTIC GMBH " 
    if  patent=="06818267": standard_name=" VETROTECH SAINT GOBAIN AG " 
    if  patent=="07399920": standard_name=" DATA COMM ELECTRONICS INC " 
    if  patent=="07812681": standard_name=" SEIKO EPSON CORPORATION " 
    if  patent=="07864340": standard_name=" ONERA " 
    if  patent=="07891016": standard_name=" IUCF HYU " 
    if  patent=="07908386": standard_name=" TELEFONAKTIEBOLAGET L M ERICSSON PUBL " 
    if patent=="04886398": standard_name="	INSTITUT FRANCAIS DU PETROLE ALSTHOM ATLANTIQUE " 
    if patent=="07171405": standard_name="	TECHNOLOGY ENABLING COMPANY LLC	" 
    if patent=="07433412": standard_name="	AT&T INTELLECTUAL PROPERTY LLP " 
    if patent=="07592433": standard_name="	UNIVERSITY OF QUEENSLAND " 
    if patent=="07598061": standard_name="	STATE OF OREGON " 
    if patent=="07792770": standard_name="	LOUISIANA TECH RESEARCH FOUNDATION " 
    if patent=="07865954": standard_name="	LOUISIANA TECH RESEARCH FOUNDATION " 
    if patent=="07893465": standard_name="	SAMSUNG ELECTRONICS CO LTD " 
    if patent=="07964409": standard_name="	LOUISIANA TECH RESEARCH FOUNDATION " 
    if patent=="08041147": standard_name="	3DHISTECH KFT " 
    if patent=="08110654": standard_name="	PEKING UNIVERSITY PEOPLES HOSPITAL " 
    if patent=="08127357": standard_name="	LOUISIANA TECH RESEARCH FOUNDATION " 
    if patent=="08232955": standard_name="	IUCF HYU " 
    if patent=="08350570": standard_name="	LOUISIANA TECH RESEARCH FOUNDATION " 
    if patent=="08367317": standard_name="	MELBOURNE HEALTH " 
    if patent=="08372958": standard_name="	BIOSYNEXUS INCORPORATED " 
    if patent=="08490628": standard_name="	RUYAN INVESTMENT LIMITED " 
    if patent=="08736452": standard_name="	LOUISIANA TECH RESEARCH FOUNDATION " 
    if patent=="08764938": standard_name="	LOUISIANA TECH RESEARCH FOUNDATION "
    if patent=="09000768": standard_name="	LOUISIANA TECH RESEARCH FOUNDATION " 
    if patent=="09068794": standard_name="	HORUS VISION LLC " 
    if patent=="08349131": standard_name="	LOUISIANA TECH RESEARCH FOUNDATION " 
    if  patent=="08436184": standard_name=" ESSILOR INTERNATIONAL " 
    if  patent=="08690324": standard_name=" ESSILOR INTERNATIONAL " 
    if  patent=="08790104": standard_name=" ESSILOR INTERNATIONAL " 
    return(standard_name)

# %%
##################################################
# Nameonly main                                  #
##################################################

def Clean_names(name, corporate_id_bool=False, adjusted=False, uspto_add_cleaning=False):
    '''Specify if want to have a bool indicating if string indicated firm and if one additional
    string cleaning should be undertaken, associated with my own additions for uspto assigness'''
    # =============================================================================
    # **
    # ** Clean Compustat name file
    # ** Bronwyn Hall, 11 Sep 2006
    # **
    # ** additions made by Jim Bessen, 1-16-07
    # ** made into nameonly_main.do from names_main_compustat2.do
    # * 	changed to be called with different files
    # * 	uses punctuation2 and combabbrev
    # *
    # * NOTE: this leaves multiple firms with same stem_name
    # *
    # set more 1
    # *global CSDIR ="C:/docume~1/HP_Owner/mydocu~1/data/pdp/freqmatch"
    # *global NAMDIR ="C:/docume~1/HP_Owner/mydocu~1/data/pdp/freqmatch"
    # *use $CSDIR/cshdr05,clear
    # =============================================================================
    #   **   Clean names
    #
    #   rename coname name
    #   rename file csfile
    #   gen file = "CS"
    #   gen asstype = "firm"
    # =============================================================================

    # Onw constribution, first stip leading and trailing white space and translate to lower
    # Then add white space around string to match description, needed for working with the strings
    standard_name = ' '+name.upper().strip()+' '

    #  gen standard_name = " "+trim(name)+" "        # ?* so we can handle words at beg and end of string*/
    # => add padding so words at beginning and end of string can be handled

     # ?*0  Special Compustat recoding */
    standard_name = standard_name.replace("-ADR"," ", 30)
    standard_name = standard_name.replace("-ADS"," ", 30)
    standard_name = standard_name.replace("-CL A "," ", 30)
    standard_name = standard_name.replace("-CL B "," ", 30)
    standard_name = standard_name.replace("-CONN "," ", 30)
    standard_name = standard_name.replace("-CONSOLIDATED "," ", 30)
    standard_name = standard_name.replace("-DEL "," ", 30)
    standard_name = standard_name.replace("-DE "," ", 30)
    standard_name = standard_name.replace("-NY SHARES "," ", 30)
    standard_name = standard_name.replace("-OLD "," ", 30)
    standard_name = standard_name.replace("-ORD "," ", 30)
    standard_name = standard_name.replace("-PRE AMEND "," ", 30) 		# ?* JB */
    standard_name = standard_name.replace("-PRE DIVEST "," ", 30) 	# ?* JB */
    standard_name = standard_name.replace("-PREAMEND "," ", 30) 		# ?* JB */
    standard_name = standard_name.replace("-PREDIVEST "," ", 30) 		# ?* JB */
    standard_name = standard_name.replace("-PROJ "," ", 30) 		# ?* JB */
    standard_name = standard_name.replace("-PROJECTED "," ", 30) 		# ?* JB */
    standard_name = standard_name.replace("-PREF "," ", 30) 		# ?* JB */
    standard_name = standard_name.replace("-PRE FASB "," ", 30) 		# ?* JB */
    standard_name = standard_name.replace("-PREFASB "," ", 30) 		# ?* JB */
    standard_name = standard_name.replace("-PRO FORMA "," ", 30)
    standard_name = standard_name.replace("- PRO FORMA "," ", 30)
    standard_name = standard_name.replace("-PRO FORMA1 "," ", 30)
    standard_name = standard_name.replace("-PRO FORMA2 "," ", 30)
    standard_name = standard_name.replace("-PRO FORMA3 "," ", 30)
    standard_name = standard_name.replace("-REDH "," ", 30)
    standard_name = standard_name.replace("-SER A COM "," ", 30)
    standard_name = standard_name.replace("-SER A "," ", 30)
    standard_name = standard_name.replace("-SPN "," ", 30)

    standard_name = standard_name.replace(" ACCPTNCE "," ACCEPTANCE ", 30)
    standard_name = standard_name.replace(" BANCORPORATION "," BANCORP ", 30)
    standard_name = standard_name.replace(" BANCORPORTN "," BANCORP ", 30)
    standard_name = standard_name.replace(" BANCRP "," BANCORP ", 30)
    standard_name = standard_name.replace(" BNCSHRS "," BANCSHARES ", 30)
    standard_name = standard_name.replace(" BRWG "," BREWING ", 30)
    standard_name = standard_name.replace(" CHEVRONTEXACO "," CHEVRON TEXACO ", 30)
    standard_name = standard_name.replace(" CHSE "," CHASE ", 30)
    standard_name = standard_name.replace(" COMMN "," COMMUNICATION ", 30)
    standard_name = standard_name.replace(" COMMUN "," COMMUNICATION ", 30)
    standard_name = standard_name.replace(" COMMUNICATNS "," COMMUNICATION ", 30)
    standard_name = standard_name.replace(" COMMUNICATIONS "," COMMUNICATION ", 30)
    standard_name = standard_name.replace(" DPT STS "," DEPT STORES ", 30)
    standard_name = standard_name.replace(" DPT "," DEPT ", 30)
    standard_name = standard_name.replace(" ENRGY "," ENERGY ", 30)
    standard_name = standard_name.replace(" FINL "," FINANCIAL ", 30)
    standard_name = standard_name.replace(" FNCL "," FINANCIAL ", 30)
    standard_name = standard_name.replace(" GRP "," GROUP ", 30)
    standard_name = standard_name.replace(" HLDGS "," HOLDINGS ", 30)
    standard_name = standard_name.replace(" HLDG "," HOLDING ", 30)
    standard_name = standard_name.replace(" HLT NTWK "," HEALTH NETWORK ", 30)
    standard_name = standard_name.replace(" HTLS RES "," HOTELS & RESORTS ", 30)
    standard_name = standard_name.replace(" HLTH "," HEALTH ", 30)
    standard_name = standard_name.replace(" INTRTECHNLGY "," INTERTECHNOLOGY ", 30)
    standard_name = standard_name.replace(" JPMORGAN "," J P MORGAN ", 30)
    standard_name = standard_name.replace(" MED OPTIC "," MEDICAL OPTICS ", 30)
    standard_name = standard_name.replace(" MINNESOTA MINING AND MANUFACTURING COMPANY "," 3M COMPANY ", 30)
    standard_name = standard_name.replace(" NAT RES "," NATURAL RESOURCES ", 30)
    standard_name = standard_name.replace(" NETWRKS "," NETWORK ", 30)
    standard_name = standard_name.replace(" PHARMACTICALS "," PHARM ", 30)
    standard_name = standard_name.replace(" PHARMACT "," PHARM ", 30)
    standard_name = standard_name.replace(" PPTYS TST "," PROPERTIES TRUST ", 30)
    standard_name = standard_name.replace(" PPTY "," PROPERTY ", 30)
    standard_name = standard_name.replace(" PROPERTY TR "," PROPERTY TRUST ", 30)
    standard_name = standard_name.replace(" PAC RAILWY "," PACIFIC RAILWAY ", 30)
    standard_name = standard_name.replace(" SEMICONDTR "," SEMICONDUCTOR ", 30)
    standard_name = standard_name.replace(" SOLU "," SOLUTIONS ", 30)
    standard_name = standard_name.replace(" ST & ALMN "," STEEL & ALUMINUM ", 30)
    standard_name = standard_name.replace(" STD "," STANDARD ", 30)
    standard_name = standard_name.replace(" TECHNOLGS "," TECH ", 30)
    standard_name = standard_name.replace(" TECHNOL "," TECH ", 30)
    standard_name = standard_name.replace(" TRANSPORTATN "," TRANSPORTATION ", 30)

    # ?* added items */
    standard_name = standard_name.replace(" ADVERTSG "," ADVERTISING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ADVNTGE "," ADVANTAGE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" AIRLN "," AIRLINES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" AIRLS "," AIRLINES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" AM "," AMERICA ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" AMER "," AMERICAN ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" APPLIAN "," APPLIANCES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" APPLICTN "," APPLICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ARCHTCTS "," ARCHITECTS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ASSD "," ASSOCIATED ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ASSOC "," ASSOCIATES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ASSOCS "," ASSOCIATES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ATOMC "," ATOMIC ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" BANCSH "," BANCSHARES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" BANCSHR "," BANCSHARES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" BCSHS "," BANCSHARES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" BK "," BANK ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" BLDGS "," BUILDINGS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" BROADCASTG "," BROADCASTING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" BTLNG "," BOTTLING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CBLVISION "," CABLEVISION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CENTRS "," CENTERS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CHAMPNSHIP "," CHAMPIONSHIP ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CMMNCTNS "," COMMUNICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CNVRSION "," CONVERSION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" COFF "," COFFEE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" COMM "," COMMUNICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" COMMUN "," COMMUNICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" COMMUNCTN "," COMMUNICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" COMMUNICTNS "," COMMUNICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" COMP "," COMPUTERS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" COMPUTR "," COMPUTER ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CONFERENCG "," CONFERENCING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CONSTRN "," CONSTR ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CONTL "," CONTINENTAL ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CONTNT "," CONTINENTAL ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CONTRL "," CONTROL ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CONTRL "," CONTROL ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CTR "," CENTER ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CTRS "," CENTERS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" CVRGS "," COVERINGS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" DEV "," DEVELOPMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" DEVL "," DEVELOPMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" DEVLP "," DEVELOPMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" DISTR "," DISTRIBUTION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" DISTRIBUT "," DISTRIBUTION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" DISTRIBUTN "," DISTRIBUTION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ELCTRNCS "," ELECTRONICS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ELECTR "," ELECTRONICS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENGNRD "," ENGINEERED ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENMT "," ENTERTAINMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENTERTAIN "," ENTERTAINMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENTERTNMNT "," ENTERTAINMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENTMNT "," ENTERTAINMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENTMT "," ENTERTAINMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENTRPR "," ENTERPRISES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENTRPRISE "," ENTERPRISES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENTRPRS "," ENTERPRISES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENVIR "," ENVIRONMENTAL ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENVIRNMNTL "," ENVIRONMENTAL ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ENVR "," ENVIRONMENTAL ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" EQUIPMT "," EQUIPMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" EXCHG "," EXCHANGE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" EXPLOR "," EXPLORATION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" FNDG "," FUNDING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" GLD "," GOLD ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" GP "," GROUP ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" HLDS "," HLDGS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" HLTHCARE "," HEALTHCARE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" HLTHCR "," HEALTHCARE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" HOMEMDE "," HOMEMADE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" HSPTL "," HOSPITAL ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ILLUM "," ILLUMINATION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INDL "," INDUSTRIAL ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INDPT "," INDEPENDENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INDTY "," INDEMNITY ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INFORMATN "," INFO ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INSTNS "," INSTITUTIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INSTRUMEN "," INSTRUMENTS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INSTRUMNT "," INSTRUMENTS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INTEGRATRS "," INTEGRATORS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INTERNATIONL "," INT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INVS "," INVESTMENTS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" INVT "," INVESTMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MANAGEMNT "," MANAGEMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MANAGMNT "," MANAGEMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MANHATN "," MANHATTAN ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MANUF "," MFG ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MDSE "," MERCHANDISING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MEASURMNT "," MEASUREMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MERCHNDSNG "," MERCHANDISING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MGMT "," MANAGEMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MGRS "," MANAGERS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MGT "," MANAGEMENT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MICROWAV "," MICROWAVE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MKTS "," MARKETS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MLTIMEDIA "," MULTIMEDIA ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MTG "," MORTGAGE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MTNS "," MOUTAINS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" MTRS "," MOTORS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" NETWRK "," NETWORK ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" NOWEST "," NORTHWEST ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" NTWRK "," NETWORK ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" OFFSHRE "," OFFSHORE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" ORGANIZTN "," ORG ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PBLG "," PUBLISHING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PHARMACEUTICL "," PHARM ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PLAST "," PLASTICS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PPTYS "," PROPERTIES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PRODS "," PROD ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PRODTN "," PRODN ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PRODUCTN "," PRODN ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PRPANE "," PROPANE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PTS "," PARTS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PUBLISH "," PUBLISHING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PUBLSHING "," PUBLISHING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PUBN "," PUBLICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PUBNS "," PUBLICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" PWR "," POWER ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" RAILRD "," RAILROAD ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" RECREATN "," RECREATION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" RECYCL "," RECYCLING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" REFIN "," REFINING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" REFNG "," REFINING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" RESTR "," RESTAURANT ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" RESTS "," RESTAURANTS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" RETAILNG "," RETAILING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" RLTY "," REALTY ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" RR "," RAILROAD ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" RSCH "," RESEARCH ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" RTNG "," RATING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SCIENTIF "," SCIENTIFIC ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SERV "," SERVICES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SLTNS "," SOLUTIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SOFTWRE "," SOFTWARE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SOLTNS "," SOLUTIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SOLUT "," SOLUTIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SRVC "," SERVICES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SRVCS "," SERVICES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" STEAKHSE "," STEAKHOUSE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" STHWST "," SOUTHWEST ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" STL "," STEEL ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" STRS "," STORES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SUP "," SUPPLY ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SUPERMKTS "," SUPERMARKETS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SUPP "," SUPPLIES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SURVYS "," SURVEYS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SVC "," SERVICES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SVCS "," SERVICES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SVSC "," SERVICES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SYS "," SYSTEMS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" SYSTM "," SYSTEMS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TCHNLGY "," TECH ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TECHNGS "," TECHNOLOGIES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TECHNL "," TECH ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TECHNLGIES "," TECHNOLOGIES ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TEL "," TELEPHONE ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TELE-COMM "," TELECOMMUNICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TELE-COMMUN "," TELECOMMUNICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TELECOMMS "," TELECOMMUNICATIONS ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TELECONFERENC "," TELECONFERENCING ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TELEG "," TELEGRAPH ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TELEGR "," TELEGRAPH ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TELVSN "," TELEVISION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TR "," TRUST ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TRANSN "," TRANSPORTATION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TRANSPORTN "," TRANSPORTATION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" TRNSACTN "," TRANSACTION ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" UTD "," UNITED ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" WSTN "," WESTERN ", 30)	 # ?* JB */
    standard_name = standard_name.replace(" WTR "," WATER ", 30)	 # ?* JB */


    standard_name=" U.S. PHILIPS CORPORATION " if standard_name.strip()=="NORTH AMERICAN PHILIPS CORP" else standard_name
    standard_name=" A. L. WILLIAMS CORP. " if standard_name.strip()=="WILLIAMS (A.L.) CORP" else standard_name
    standard_name=" B. F. GOODRICH CO. " if standard_name.strip()=="GOODRICH CORP" else standard_name
    standard_name=" BELL + HOWELL COMPANY " if standard_name.strip()=="BELL & HOWELL OPERATING CO" else standard_name
    standard_name=" BENDIX CORPORATION(NOW ALLIED-SIGNAL INC.) " if standard_name.strip()=="BENDIX CORP" else standard_name
    standard_name=" BORG-WARNER CORPORATION " if standard_name.strip()=="BORGWARNER INC" else standard_name
    standard_name=" CHRYSLER MOTORS CORPORATION " if standard_name.strip()=="CHRYSLER CORP" else standard_name
    standard_name=" CISCO TECHNOLOGY, INC. " if standard_name.strip()=="CISCO SYSTEMS INC" else standard_name
    standard_name=" DELL PRODUCTS, L.P. " if standard_name.strip()=="DELL INC" else standard_name
    standard_name=" DELPHI TECHNOLOGIES, INC. " if standard_name.strip()=="DELPHI CORP" else standard_name
    standard_name=" E. I. DU PONT DE NEMOURS AND COMPANY " if standard_name.strip()=="DU PONT (E I) DE NEMOURS" else standard_name
    standard_name=" E. R. SQUIBB + SONS, INC. " if standard_name.strip()=="SQUIBB CORP" else standard_name
    standard_name=" ELI LILLY AND COMPANY " if standard_name.strip()=="LILLY (ELI) & CO" else standard_name
    standard_name=" G. D. SEARLE & CO. " if standard_name.strip()=="SEARLE (G.D.) & CO" else standard_name
    standard_name=" MINNESOTA MINING AND MANUFACTURING COMPANY " if standard_name.strip()=="3M CO" else standard_name
    standard_name=" OWENS-CORNING FIBERGLAS CORPORATION " if standard_name.strip()=="OWENS CORNING" else standard_name
    standard_name=" SCHLUMBERGER TECHNOLOGY CORPORATION " if standard_name.strip()=="SCHLUMBERGER LTD" else standard_name
    standard_name=" SCI-MED LIFE SYSTEMS, INC. " if standard_name.strip()=="SICMED LIFE SYSTEMS" else standard_name
    standard_name=" TDK CORPORATION " if standard_name.strip()=="TDK CORP" else standard_name
    standard_name=" UNITED STATES SURGICAL CORPORATION " if standard_name.strip()=="U S SURGICAL CORP" else standard_name
    standard_name=" W. R. GRACE & CO. " if standard_name.strip()=="GRACE (W R) & CO" else standard_name
    standard_name=" WESTINGHOUSE ELECTRIC CORP. " if standard_name.strip()=="WESTINGHOUSE ELEC" else standard_name

    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------    
    if uspto_add_cleaning:
        # =============================================================================
        # ******************************************************************************************************
        # ** PROCEDURE 0 SPECIAL RECODE FOR USPTO NAMES
        # **
        # ** Additions made for USPTO dataset by BHH  August 2006
        # * jb 1/15/08 -> index => strpos
        # **
        # ******************************************************************************************************
        # =============================================================================

        standard_name = standard_name.replace("-CONN.","", 1)
        #standard_name = standard_name.replace(";"," ; ")
        
        #----------------------------------------------
        if adjusted:
            #!!! Remove any notions of text in brackets as well as additions like ', the ****' or ', a ****'
            standard_name = re.sub("\\s{1,}licensing$|,\\s{1,}the\\s{1,}.*$|,\\s{1,}a.*$", '', standard_name, 1, re.IGNORECASE)

    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------
    
    # # ?*1*/ do $NAMDIR/punctuation2
    standard_name = punctuation(standard_name, uspto_add_cleaning)

    
    # # ?*2*/ qui do $NAMDIR/standard_name
    standard_name = standard_naming(standard_name)

    # # ?*3*/
    #  qui do $NAMDIR/corporates
    # => classification, ignore if no requestes
    if corporate_id_bool:
        type_firm = corporates_bool(standard_name)

    # # ?* 3b */
    standard_name = combabbrev(standard_name)

    #====================================================================
    # I add aditional string adjustments that can be useful
    if adjusted:
        standard_name = re.sub(" hld "," HLDGS ", standard_name, 30, re.IGNORECASE)
        standard_name = re.sub(" inds "," IND ", standard_name, 30, re.IGNORECASE)
        standard_name = re.sub(" assn "," ASSOC ", standard_name, 30, re.IGNORECASE)
        standard_name = re.sub(" bldg "," BUILDING ", standard_name, 30, re.IGNORECASE)
        standard_name = re.sub(" centr "," CENT ", standard_name, 30, re.IGNORECASE)
        standard_name = re.sub(" westn "," WESTERN ", standard_name, 30, re.IGNORECASE)
        standard_name = re.sub(" pharmactls "," PHARM ", standard_name, 30, re.IGNORECASE)
    #====================================================================

    
    #replace assignee_std=itrim(assignee_std)

    # # ?*4*/ qui do $NAMDIR/stem_name
    stemmed_name = stem_name(standard_name)
    # # ?*5*/ replace stem_name = trim(stem_name)

    # Return stem only if not firm identification is requested
    if corporate_id_bool:
        return(standard_name.strip(), stemmed_name.strip(), type_firm)
    else:
        return(standard_name.strip(), stemmed_name.strip())




