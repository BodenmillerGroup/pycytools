class ObjectRelations:
    MODULE = 'Module'
    RELATIONSHIP = 'Relationship'
    FIRST_OBJ_NAME = 'First Object Name'
    SECOND_OBJ_NAME = 'Second Object Name'
    FIRST_OBJ_NUMBER = 'First Object Number'
    SECOND_OBJ_NUMBER = 'Second Object Number'
    FIRST_IMG_NUMBER = 'First Image Number'
    SECOND_IMG_NUMBER = 'Second Image Number'

    OBJ_NUMBER = 'ObjectNumber'
    IMG_NUMBER = 'ImageNumber'
    OBJ_ID = 'ObjectId'

    NEIGHBORS = 'Neighbors'
    CHILD = 'Child'
    PARENT = 'Parent'

    def __init__(self, dat_obj_rel):
        neighbours = {}
        parent = {}
        child = {}
        for (rel, f, s), d in (dat_obj_rel
                .groupby([self.RELATIONSHIP,
                          self.FIRST_OBJ_NAME,
                          self.SECOND_OBJ_NAME])):
            if rel == self.NEIGHBORS:
                neighbours[f] = d[[self.FIRST_OBJ_NUMBER,
                                   self.FIRST_IMG_NUMBER,
                                   self.SECOND_OBJ_NUMBER,
                                   self.SECOND_IMG_NUMBER]]
            elif rel == self.CHILD:
                dic = child.get(f, {})
                dic[s] = d[[self.FIRST_OBJ_NUMBER,
                            self.FIRST_IMG_NUMBER,
                            self.SECOND_OBJ_NUMBER,
                            self.SECOND_IMG_NUMBER]]
                child[f] = dic

            elif rel == self.PARENT:
                dic = parent.get(f, {})
                dic[s] = d[[self.FIRST_OBJ_NUMBER,
                            self.FIRST_IMG_NUMBER,
                            self.SECOND_OBJ_NUMBER,
                            self.SECOND_IMG_NUMBER]]
                parent[f] = dic
            else:
                warnings.WarningMessage(f'{rel} relationship not supported')

            self.neighbours = neighbours
            self.child = child
            self.parent = parent

    def get_vars_via_rel(self, rel, value_vars, objectname_1, dat_1, objectname_2=None, dat_2=None):
        if rel == self.NEIGHBORS:
            assert (objectname_2 is None) or (objectname_2 == objectname_1), f'Objectnames need to agree for {rel}'
            dat_rel = self.neighbours[objectname_1]
            dat_2 = dat_1
        elif rel == self.CHILD:
            dat_rel = self.child[objectname_1][objectname_2]
        elif rel == self.PARENT:
            dat_rel = self.parent[objectname_1][objectname_2]

        dat_merged = (dat_1[[self.OBJ_NUMBER, self.IMG_NUMBER]].reset_index(drop=False)
                      .merge(dat_rel, left_on=[self.OBJ_NUMBER, self.IMG_NUMBER],
                             right_on=[self.FIRST_OBJ_NUMBER, self.FIRST_IMG_NUMBER])
                      .dropna()
                      .drop(columns=[self.OBJ_NUMBER, self.IMG_NUMBER,
                                     self.FIRST_OBJ_NUMBER, self.FIRST_IMG_NUMBER])
                      .merge(dat_2[[self.OBJ_NUMBER, self.IMG_NUMBER, *value_vars]],
                             right_on=[self.OBJ_NUMBER, self.IMG_NUMBER],
                             left_on=[self.SECOND_OBJ_NUMBER, self.SECOND_IMG_NUMBER])
                      .drop(columns=[self.OBJ_NUMBER, self.IMG_NUMBER, self.SECOND_OBJ_NUMBER, self.SECOND_IMG_NUMBER])
                      .set_index(OBJ_ID)
                      )
        return dat_merged