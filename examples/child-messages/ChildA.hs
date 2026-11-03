{-# LANGUAGE DeriveAnyClass #-}
{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE DerivingStrategies #-}
{-# LANGUAGE OverloadedStrings #-}
module ChildA (MsgA (..), childA) where

import GHC.Generics (Generic)
import Miso
import qualified Miso.Html as H
import Miso.JSON (FromJSON, ToJSON)
import Miso.String (ms)

-- The child owns its message type. It does not import its parent.
newtype MsgA = MsgA Int
  deriving stock (Eq, Show, Generic)
  deriving anyclass (ToJSON, FromJSON)

data ActionA = SendA

childA
  :: ToJSON message
  => (MsgA -> message)
  -> Component context () Int ActionA
childA toParent = component 0 updateA viewA
  where
    updateA SendA = do
      modify (+ 1)
      mailParent (toParent (MsgA 7))

    viewA sent = H.section_ []
      [ H.button_ [textProp "id" "send-a", H.onClick SendA] [text "Send A (7)"]
      , H.p_ [] [text "Child A sends: ", H.span_ [textProp "id" "child-a-sent"] [text (ms sent)]]
      ]
