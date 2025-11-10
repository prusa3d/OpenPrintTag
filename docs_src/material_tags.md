# Material tags
Material tags provide an additional boolean-style parameters to the filament.
1. If a tag is not present for the material, it SHALL be interpreted as "it is unknown whether the material has this tag" instead of "it is known that the material does not have this tag".
1. New tags CAN be introduced in futher revisions of the standard. Tags also CAN be removed.
1. The tags have defined implications. If a material has a tag X, it MUST include all tags listed in the `implies` column as well. This rule applies transitively.
1. The `implies` relation transitivity MUST NOT change between standard revisions for existing tags.
    1. If we have tag implications A → C, we CAN add a tag B that changes implications to A → B → C.
    1. If we have tag implications A → B → C, we CAN remove tag B while changing implications to A → C.

## Tags list
{{ material_tag_table() }}
